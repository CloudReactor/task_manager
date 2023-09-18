from typing import Any, FrozenSet, Optional, Tuple, TYPE_CHECKING, cast

from dataclasses import dataclass
import logging
import random
import re
import string
import uuid

from django.utils import timezone

from rest_framework.exceptions import APIException

from pydantic import BaseModel

from botocore.exceptions import ClientError

from ..common.aws import *
from ..common.utils import coalesce, deepmerge
from .aws_settings import INFRASTRUCTURE_TYPE_AWS, AwsNetworkSettings, AwsSettings
from .aws_cloudwatch_scheduling_settings import (
    SCHEDULING_TYPE_AWS_CLOUDWATCH,
    AwsCloudwatchSchedulingSettings
)
from .aws_base_execution_method import AwsBaseExecutionMethod

if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )

from .execution_method import ExecutionMethod


logger = logging.getLogger(__name__)


SERVICE_PROVIDER_AWS_ECS = 'AWS ECS'


class AwsEcsExecutionMethodSettings(BaseModel):
    launch_type: Optional[str] = None
    supported_launch_types: Optional[list[str]] = None
    cluster_arn: Optional[str] = None
    cluster_infrastructure_website_url: Optional[str] = None
    task_definition_arn: Optional[str] = None
    task_definition_infrastructure_website_url: Optional[str] = None
    infrastructure_website_url: Optional[str] = None
    main_container_name: Optional[str] = None
    execution_role_arn: Optional[str] = None
    execution_role_infrastructure_website_url: Optional[str] = None
    task_role_arn: Optional[str] = None
    task_role_infrastructure_website_url: Optional[str] = None
    platform_version: Optional[str] = None
    enable_ecs_managed_tags: Optional[bool] = None
    propagate_tags: Optional[str] = None
    enable_execute_command: Optional[bool] = None
    task_group: Optional[str] = None

    def update_derived_attrs(self, aws_settings: Optional[AwsSettings]) -> None:
        if aws_settings:
            aws_account_id = aws_settings.account_id
            region = aws_settings.region

            if aws_account_id and region:
                if self.cluster_arn and not self.cluster_arn.startswith('arn:'):
                    self.cluster_arn = 'arn:aws:ecs:' + region + ':' + \
                        + aws_account_id + ':cluster/' + self.cluster_arn

                if self.execution_role_arn:
                    self.execution_role_arn = normalize_role_arn(self.execution_role_arn,
                            aws_account_id=aws_account_id, region=region)

                if self.task_role_arn:
                    self.task_role_arn = normalize_role_arn(self.task_role_arn,
                            aws_account_id=aws_account_id, region=region)

        self.cluster_infrastructure_website_url = \
            make_aws_console_ecs_cluster_url(self.cluster_arn)

        self.task_definition_infrastructure_website_url = \
            make_aws_console_ecs_task_definition_url(self.task_definition_arn)

        # Just a copy of the task definition URL, overwritten by
        # AwsEcsExecutionMethodInfo.update_derived_attrs()
        self.infrastructure_website_url = self.task_definition_infrastructure_website_url

        self.execution_role_infrastructure_website_url = \
            make_aws_console_role_url(self.execution_role_arn)

        self.task_role_infrastructure_website_url = \
            make_aws_console_role_url(self.task_role_arn)


class AwsEcsExecutionMethodInfo(AwsEcsExecutionMethodSettings):
    task_arn: Optional[str] = None

    def update_derived_attrs(self, aws_settings: Optional[AwsSettings]):
        super().update_derived_attrs(aws_settings=aws_settings)

        self.infrastructure_website_url = None

        if self.task_arn and self.cluster_arn:
            parts = self.task_arn.split(':')
            aws_region = parts[3]

            if aws_region:
                last_part = parts[5]
                last_part_parts = last_part.split('/')
                if len(last_part_parts) < 3:
                    cluster_name = extract_cluster_name(self.cluster_arn)
                    task_id = last_part_parts[1]
                else:
                    cluster_name = last_part_parts[1]
                    task_id = last_part_parts[2]

                if cluster_name is None:
                    logger.warning("Task.infrastructure_website_url() can't determine cluster_name")
                else:
                    self.infrastructure_website_url = AWS_CONSOLE_BASE_URL \
                        + 'ecs/home?region=' \
                        + quote(aws_region) + '#/clusters/' \
                        + quote(cluster_name) + '/tasks/' \
                        + quote(task_id) + '/details'


class AwsEcsServiceDeploymentCircuitBreaker(BaseModel):
    enable: Optional[bool] = None
    rollback_on_failure: Optional[bool] = None


class AwsEcsServiceDeploymentConfiguration(BaseModel):
    maximum_percent: Optional[int] = None
    minimum_healthy_percent: Optional[int] = None
    deployment_circuit_breaker: Optional[AwsEcsServiceDeploymentCircuitBreaker] = None


class AwsApplicationLoadBalancer(BaseModel):
    target_group_arn: Optional[str] = None
    target_group_infrastructure_website_url: Optional[str] = None
    container_name: Optional[str] = None
    container_port: Optional[int] = None

    def update_derived_attrs(self, task: 'Task',
            aws_settings: Optional[AwsSettings]) -> None:
        self.target_group_infrastructure_website_url = None

        if self.target_group_arn:
            region = task.run_environment.aws_default_region

            if aws_settings and aws_settings.network:
                region = aws_settings.network.region or region

            if region:
                self.target_group_infrastructure_website_url = \
                    f"https://{region}.console.aws.amazon.com/ec2/v2/home?" \
                    + f"region={region}#TargetGroup:targetGroupArn=" \
                    + self.target_group_arn

class AwsApplicationLoadBalancerSettings(BaseModel):
    health_check_grace_period_seconds: Optional[int] = None
    load_balancers: Optional[list[AwsApplicationLoadBalancer]] = None

    def update_derived_attrs(self, task: 'Task',
            aws_settings: Optional[AwsSettings]) -> None:
        if self.load_balancers:
            for load_balancer in self.load_balancers:
                load_balancer.update_derived_attrs(task=task,
                    aws_settings=aws_settings)

@dataclass
class AwsEcsServiceResponseFragment:
    service_dict: dict[str, Any]
    last_status: str
    service_arn: str
    service_name: str
    next_service_name_suffix: Optional[int] = None

    @staticmethod
    def from_boto_service_response_fragment(service_dict: dict[str, Any]) -> 'AwsEcsServiceResponseFragment':
        sd = service_dict
        service_name = sd['serviceName']
        service_arn = sd['serviceArn']
        last_status = sd['status'].upper()
        index: Optional[int] = None

        logger.info(f"Last status of service '{service_name}' with ARN '{service_arn}' is {last_status}")

        if last_status in ('DRAINING', 'ACTIVE', 'INACTIVE'):
            m = AwsEcsExecutionMethod.SERVICE_NAME_REGEX.match(service_name)

            if m:
                index_str = m.group(3)
                if index_str:
                    index = int(index_str)
                    if last_status != 'INACTIVE':
                        index += 1
            else:
                logger.warning(f"Can't match service name '{service_name}', will use 0 as suffix")
        else:
            logger.warning(f"Unexpected service status {last_status}")

        return AwsEcsServiceResponseFragment(
            service_dict = sd,
            last_status = last_status,
            service_arn = service_arn,
            service_name = service_name,
            next_service_name_suffix=index
        )

@dataclass
class AwsEcsServiceTeardownResult:
    service_info: Optional[AwsEcsServiceResponseFragment] = None


class AwsEcsServiceSettings(BaseModel):
    deployment_configuration: Optional[AwsEcsServiceDeploymentConfiguration] = None
    scheduling_strategy: Optional[str] = None
    force_new_deployment: Optional[bool] = None
    load_balancer_settings: Optional[AwsApplicationLoadBalancerSettings] = None
    enable_ecs_managed_tags: Optional[bool] = None
    propagate_tags: Optional[str] = None
    tags: Optional[dict[str, str]] = None
    service_arn: Optional[str] = None
    infrastructure_website_url: Optional[str] = None

    def update_derived_attrs(self, task: 'Task',
            aws_ecs_settings: AwsEcsExecutionMethodSettings,
            aws_settings: Optional[AwsSettings]):
        cluster_name = extract_cluster_name(aws_ecs_settings.cluster_arn)

        if cluster_name and self.service_arn:
            self.infrastructure_website_url = make_aws_console_ecs_service_url(
                ecs_service_arn=self.service_arn,
                cluster_name=cluster_name)
        else:
            self.infrastructure_website_url = None

        if self.load_balancer_settings:
            self.load_balancer_settings.update_derived_attrs(task=task,
                aws_settings=aws_settings)

    @staticmethod
    def from_boto_service_response_fragment(service_dict: dict[str, Any]) -> 'AwsEcsServiceSettings':
        sd = service_dict

        ss = AwsEcsServiceSettings(
            service_arn=sd.get('serviceArn'),
            scheduling_strategy=sd.get('schedulingStrategy'),
            enable_ecs_managed_tags=sd.get('enableECSManagedTags'),
            propagate_tags=sd.get('propagateTags')
        )

        dc = sd.get('deploymentConfiguration')

        if dc:
            parsed_dcb: Optional[AwsEcsServiceDeploymentCircuitBreaker] = None

            dcb = dc.get('deploymentCircuitBreaker')
            if dcb:
                parsed_dcb = AwsEcsServiceDeploymentCircuitBreaker(
                    enable=dcb.get('enable'),
                    rollback=dcb.get('rollback')
                )

            ss.deployment_configuration = AwsEcsServiceDeploymentConfiguration(
                maximum_percent=dc.get('maximumPercent'),
                minimum_healthy_percent=dc.get('minimumHealthyPercent'),
                deployment_circuit_breaker=parsed_dcb
            )

        lbs = sd.get('loadBalancers')

        if lbs:
            parsed_lbs = []
            for lb in lbs:
                parsed_lbs.append(AwsApplicationLoadBalancer(
                    target_group_arn=lb.get('targetGroupArn'),
                    container_name=lb.get('containerName'),
                    container_port=lb.get('containerPort')
                ))

            ss.load_balancer_settings = AwsApplicationLoadBalancerSettings(
                health_check_grace_period_seconds=sd.get('healthCheckGracePeriodSeconds'),
                load_balancers=parsed_lbs
            )

        tags = sd.get('tags')

        if tags:
            parsed_tags = {}
            for tag in tags:
                k = tag.get('key')
                v = tag.get('value')
                if (k is not None) and (v is not None):
                    parsed_tags[k] = v

            ss.tags = parsed_tags

        return ss

class AwsEcsExecutionMethod(AwsBaseExecutionMethod):
    NAME = 'AWS ECS'

    LAUNCH_TYPE_EC2 = 'EC2'
    LAUNCH_TYPE_FARGATE = 'FARGATE'
    ALL_LAUNCH_TYPES = [LAUNCH_TYPE_FARGATE, LAUNCH_TYPE_EC2]
    DEFAULT_LAUNCH_TYPE = LAUNCH_TYPE_FARGATE
    DEFAULT_CPU_UNITS = 256
    DEFAULT_MEMORY_MB = 512

    SERVICE_NAME_REGEX = re.compile(r"^(.+?)(_(\d+))?$")

    DEFAULT_LOAD_BALANCER_HEALTH_CHECK_GRACE_PERIOD_SECONDS = 300

    SERVICE_PROPAGATE_TAGS_TASK_DEFINITION = 'TASK_DEFINITION'
    SERVICE_PROPAGATE_TAGS_SERVICE = 'SERVICE'

    SERVICE_PROPAGATE_TAGS_CHOICES = [
        SERVICE_PROPAGATE_TAGS_TASK_DEFINITION,
        SERVICE_PROPAGATE_TAGS_SERVICE,
    ]

    CAPABILITIES_WITHOUT_SCHEDULING = frozenset([
        ExecutionMethod.ExecutionCapability.MANUAL_START,
        ExecutionMethod.ExecutionCapability.SETUP_SERVICE
    ])

    MAX_TAG_COUNT = 50

    EXECUTION_METHOD_ATTRIBUTES_REQUIRING_SCHEDULING_UPDATE = [
        'task_definition_arn',
        'launch_type',
        'cluster_arn',
        'platform_version',
        'execution_role_arn',
    ]

    NETWORK_ATTRIBUTES_REQUIRING_SCHEDULING_UPDATE = [
        'subnets',
        'security_groups',
        'assign_public_ip'
    ]


    def __init__(self,
            task: Optional['Task'] = None,
            task_execution: Optional['TaskExecution'] = None,
            aws_settings: Optional[dict[str, Any]] = None,
            aws_ecs_settings: Optional[dict[str, Any]] = None) -> None:
        super().__init__(self.NAME, task=task, task_execution=task_execution,
                aws_settings=aws_settings)

        task = self.task

        if aws_ecs_settings is None:
            aws_ecs_settings = self.merge_aws_ecs_settings_dict(task=task,
                task_execution=task_execution)

        logger.debug(f"{aws_ecs_settings=}")

        if task_execution:
            self.settings = cast(AwsEcsExecutionMethodSettings,
                    AwsEcsExecutionMethodInfo.parse_obj(aws_ecs_settings))
        else:
            self.settings = AwsEcsExecutionMethodSettings.parse_obj(aws_ecs_settings)

        self.service_settings: Optional[AwsEcsServiceSettings] = None
        self.scheduling_settings: Optional[AwsCloudwatchSchedulingSettings] = None

        if task and (task_execution is None):
            if task.service_settings is not None:
                self.service_settings = AwsEcsServiceSettings.parse_obj(task.service_settings)

            if task.scheduling_settings is not None:
                self.scheduling_settings = AwsCloudwatchSchedulingSettings.parse_obj(
                    task.scheduling_settings)


    @staticmethod
    def merge_aws_ecs_settings_dict(task: Optional['Task'],
            task_execution: Optional['TaskExecution']) -> dict[str, Any]:

        settings_to_merge: list[dict[str, Any]] = [ {} ]

        if task:
            settings_to_merge = [
                task.run_environment.default_aws_ecs_configuration or {},
                task.execution_method_capability_details or {}
            ]

        if task_execution and task_execution.execution_method_details:
            settings_to_merge.append(task_execution.execution_method_details)

        return deepmerge(*settings_to_merge)


    def capabilities(self) -> FrozenSet[ExecutionMethod.ExecutionCapability]:
        task = self.task

        if task and task.passive:
            return frozenset()

        aws_settings = self.aws_settings

        if not aws_settings.can_manage_infrastructure():
            logger.debug("Can't control ECS")
            return frozenset()

        network = self.aws_settings.network

        subnets: Optional[list[str]] = None

        if network:
            subnets = network.subnets

        if not subnets:
            return frozenset()

        return ExecutionMethod.ALL_CAPABILITIES


    def should_update_or_force_recreate_scheduled_execution(self,
            old_execution_method: Optional[ExecutionMethod]=None) \
            -> Tuple[bool, bool]:
        should = super().should_maybe_update_scheduled_execution(
                old_execution_method=old_execution_method)

        if should is not None:
            return (should, True)

        if old_execution_method is None:
            return (True, True)

        network = self.aws_settings.network

        if network is None:
            logger.warning("should_update_scheduled_execution(): No network settings found, returning true so an exception happens later")
            return (True, True)

        old_task = old_execution_method.task

        if (not old_task) or (old_task.execution_method_capability_details is None) or \
            (old_task.execution_method_type != AwsEcsExecutionMethod.NAME) or \
            (old_task.infrastructure_settings is None) or \
            (old_task.infrastructure_type != INFRASTRUCTURE_TYPE_AWS):
            return (True, True)

        old_aws_ecs_execution_method = cast(AwsEcsExecutionMethod, old_execution_method)
        old_settings = old_aws_ecs_execution_method.settings

        for attr in self.EXECUTION_METHOD_ATTRIBUTES_REQUIRING_SCHEDULING_UPDATE:
            old_value = getattr(old_settings, attr)
            new_value = getattr(self.settings, attr)

            if new_value != old_value:
                logger.info(f"{attr} changed from {old_value} to {new_value}, adjusting schedule")
                return (True, True)

        old_aws_settings = old_aws_ecs_execution_method.aws_settings
        old_network = old_aws_settings.network

        if old_network is None:
            logger.info("should_update_scheduled_execution() Task previously had no network settings, returning true")
            return (True, True)

        for attr in self.NETWORK_ATTRIBUTES_REQUIRING_SCHEDULING_UPDATE:
            old_value = getattr(old_network, attr)
            new_value = getattr(network, attr)

            if new_value != old_value:
                logger.info(f"{attr} changed from {old_value} to {new_value}, adjusting schedule")
                return (True, True)

        return (False, False)


    def setup_scheduled_execution(self, old_execution_method: Optional[ExecutionMethod]=None,
            force_creation: bool=False, teardown_result: Optional[Any]=None) -> None:
        task = self.task

        if not task:
            raise RuntimeError("No Task found")

        if not task.has_active_managed_scheduled_execution(current=False):
            raise RuntimeError("setup_scheduled_execution() called but the Task is not going to be actively scheduled")

        if task.scheduling_provider_type and \
                (task.scheduling_provider_type != SCHEDULING_TYPE_AWS_CLOUDWATCH):
            raise RuntimeError(f"setup_scheduled_execution() called but {task.scheduling_provider_type=} is unsupported")

        if not task.schedule.startswith('cron') and not task.schedule.startswith('rate'):
            raise APIException(detail=f"Schedule '{task.schedule}' is invalid")

        aws_scheduled_execution_rule_name = f"CR_{task.uuid}"

        client = self.aws_settings.make_events_client()

        ss = self.scheduling_settings or AwsCloudwatchSchedulingSettings()

        kwargs = {
            'Name': aws_scheduled_execution_rule_name,
            'ScheduleExpression': task.schedule,
            #EventPattern='true',
            'State': 'ENABLED',
            'Description': f"Scheduled execution of Task '{task.name}' ({task.uuid})"
        }
            # TODO: use add_creation_args()
            # Tags=[
            #     {
            #         'Key': 'string',
            #         'Value': 'string'
            #     },
            # ],

        execution_role_arn = self.settings.execution_role_arn
        logger.info(f"Using execution role arn = '{execution_role_arn}'")

        if execution_role_arn:
            kwargs['RoleArn'] = execution_role_arn

        if ss.event_bus_name:
            kwargs['EventBusName'] = ss.event_bus_name

        # Need this permission: https://github.com/Miserlou/Zappa/issues/381
        response = client.put_rule(**kwargs)

        aws_scheduled_event_rule_arn = response['RuleArn']
        logger.info(f"got rule ARN = {aws_scheduled_event_rule_arn}")

        # Delete these once scheduling_settings is the source of truth
        task.aws_scheduled_execution_rule_name = aws_scheduled_execution_rule_name
        task.aws_scheduled_event_rule_arn = aws_scheduled_event_rule_arn

        ss.execution_rule_name = aws_scheduled_execution_rule_name
        ss.event_rule_arn = aws_scheduled_event_rule_arn

        self.scheduling_settings = ss

        task.is_scheduling_managed = True
        task.scheduling_provider_type = SCHEDULING_TYPE_AWS_CLOUDWATCH
        task.scheduling_settings = ss.dict()

        client.enable_rule(Name=aws_scheduled_execution_rule_name)

        aws_event_target_rule_name = f"CR_{task.uuid}"
        aws_event_target_id = f"CR_{task.uuid}"
        platform_version = self.settings.platform_version or \
                AWS_ECS_PLATFORM_VERSION_LATEST

        task_network = self.aws_settings.network

        if not task_network:
            raise APIException("Cannot schedule Task: no network settings found")

        assign_public_ip = self.assign_public_ip_str()

        response = client.put_targets(
            Rule=aws_event_target_rule_name,
            Targets=[
                {
                    'Id': aws_event_target_id,
                    'Arn': self.settings.cluster_arn,
                    'RoleArn': self.aws_settings.events_role_arn,
                    'EcsParameters': {
                        'TaskDefinitionArn': self.settings.task_definition_arn,
                        'TaskCount': task.scheduled_instance_count or 1,
                        'LaunchType': self.settings.launch_type or self.DEFAULT_LAUNCH_TYPE,
                        # Only for tasks that use awsvpc networking
                        'NetworkConfiguration': {
                            'awsvpcConfiguration': {
                                'Subnets': task_network.subnets,
                                'SecurityGroups': task_network.security_groups,
                                'AssignPublicIp': assign_public_ip
                            }
                        },
                        'PlatformVersion': platform_version,
                        #'Group': 'string'
                    },
                },
            ]
        )
        handle_aws_multiple_failure_response(response)

        # Remove these once scheduling_settings is the source of truth
        task.aws_event_target_rule_name = aws_event_target_rule_name
        task.aws_event_target_id = aws_event_target_id

        ss.event_target_rule_name = aws_event_target_rule_name
        ss.event_target_id = aws_event_target_id

        task.scheduling_settings = ss.dict()


    def teardown_scheduled_execution(self) -> Tuple[Optional[dict[str, Any]], Optional[Any]]:
        task = self.task

        if not task:
            raise RuntimeError("No Task found")

        if task.is_scheduling_managed is False:
            return (None, None)

        if task.scheduling_provider_type and \
                (task.scheduling_provider_type != SCHEDULING_TYPE_AWS_CLOUDWATCH):
            raise RuntimeError(f"teardown_scheduled_execution() called but {task.scheduling_provider_type=} is unsupported")

        ss = self.scheduling_settings

        if not ss:
            if task.is_scheduling_managed:
                task.is_scheduling_managed = None
                task.scheduling_provider_type = ''
            return (None, None)

        client: Optional[Any] = None

        if ss.event_target_rule_name and ss.event_target_id:
            client = self.aws_settings.make_events_client()

            try:
                kwargs = {
                    'Rule': ss.event_target_rule_name,
                    'Ids': [
                        ss.event_target_id
                    ],
                    'Force': False
                }

                if ss.event_bus_name:
                    kwargs['EventBusName'] = ss.event_bus_name

                response = client.remove_targets(**kwargs)
                handle_aws_multiple_failure_response(response)
            except ClientError as client_error:
                error_code = client_error.response['Error']['Code']
                # Happens if the schedule rule is removed manually
                if error_code == 'ResourceNotFoundException':
                    logger.warning(f"teardown_scheduled_execution(): Can't remove target {ss.event_target_rule_name} because resource not found, exception = {client_error}")
                else:
                    logger.exception(f"teardown_scheduled_execution(): Can't remove target {ss.event_target_rule_name} due to unhandled error {error_code}")
                    raise client_error

            # Remove when scheduling_settings is the source of truth
            task.aws_event_target_rule_name = ''
            task.aws_event_target_id = ''

            ss.event_target_rule_name = None
            ss.event_target_id = None
            self.scheduling_settings = ss
            task.scheduling_settings = ss.dict()

        if ss.execution_rule_name:
            client = client or self.aws_settings.make_events_client()

            try:
                kwargs = {
                    'Name': ss.execution_rule_name,
                    'Force': True
                }

                if ss.event_bus_name:
                    kwargs['EventBusName'] = ss.event_bus_name

                client.delete_rule(**kwargs)
            except ClientError as client_error:
                error_code = client_error.response['Error']['Code']
                # Happens if the schedule rule is removed manually
                if error_code == 'ResourceNotFoundException':
                    logger.warning(
                        f"teardown_scheduled_execution(): Can't delete rule {ss.execution_rule_name} because resource not found, exception = {client_error}")
                else:
                    logger.exception(
                        f"teardown_scheduled_execution(): Can't delete rule {ss.execution_rule_name} due to unhandled error {error_code}")
                    raise client_error

            # TODO: Remove when scheduling_settings becomes source of truth
            task.aws_scheduled_event_rule_arn = ''

            ss.execution_rule_name = None
            ss.event_rule_arn = None

            self.scheduling_settings = ss
            task.scheduling_settings = ss.dict()
            task.is_scheduling_managed = None

        return (task.scheduling_settings, None)

    def should_update_or_force_recreate_service(self, old_execution_method: Optional[ExecutionMethod]=None) -> Tuple[bool, bool]:
        task = self.task

        if not task:
            raise RuntimeError("No Task found")

        will_be_managed_service = task.is_active_managed_service(current=False)

        old_task: Optional[Task] = None
        old_aws_ecs_execution_method: Optional[AwsEcsExecutionMethod] = None

        if old_execution_method:
            old_task = old_execution_method.task

            if isinstance(old_execution_method, AwsEcsExecutionMethod):
                old_aws_ecs_execution_method = cast(AwsEcsExecutionMethod,
                        old_execution_method)

        was_managed_ecs_service = bool(old_task and old_aws_ecs_execution_method and \
                old_task.is_active_managed_service() and \
                (old_task.service_provider_type == SERVICE_PROVIDER_AWS_ECS) and \
                old_aws_ecs_execution_method.service_settings and \
                old_aws_ecs_execution_method.service_settings.service_arn)

        logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {was_managed_ecs_service=}, {will_be_managed_service=}")

        if not will_be_managed_service:
            return (was_managed_ecs_service, False)

        if task.service_provider_type != SERVICE_PROVIDER_AWS_ECS:
            raise APIException(f"Unsupported service provider '{task.service_provider_type}'")

        ss = self.service_settings

        logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} service_settings = {ss}")

        if not was_managed_ecs_service:
            logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} was_managed_ecs_service=false, forcing recreate")
            return (True, True)

        if (not old_task) or (old_task.service_settings is None) or \
                (not old_aws_ecs_execution_method):
            logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} missing old_aws_ecs_execution_method, forcing recreate")
            return (True, True)

        try:
            old_settings = old_aws_ecs_execution_method.settings

            logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {old_settings=}")

            if (old_settings.launch_type != self.settings.launch_type) or \
                  (old_settings.cluster_arn != self.settings.cluster_arn):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} launch type or cluster differs, forcing recreate")
                return (True, True)

            old_ss = old_aws_ecs_execution_method.service_settings

            if (not old_ss) or (not old_ss.service_arn):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} old service settings = {old_ss} missing service_arn, forcing recreate")
                return (True, True)

            if ss and ss.service_arn and (ss.service_arn != old_ss.service_arn):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {ss.service_arn=} != {old_ss.service_arn=}, forcing recreate")
                return (True, True)

            old_aws_settings = old_aws_ecs_execution_method.aws_settings

            if not old_aws_settings:
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} missing old AWS settings, update required but not recreate")
                return (True, False)

            old_network = old_aws_settings.network
            if not old_network:
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {old_aws_settings=} missing network, update required but not recreate")
                return (True, False)

            # TODO: network cannot change for non-ECS deployment controllers
            # if (not old_network) or (not old_network.subnets):
            #     return (True, True)

            # TODO: load balancers cannot change for non-ECS deployment controllers
            # old_lbs = old_ss.load_balancer_settings
            # lbs = ss.load_balancer_settings

            # if lbs:
            #     lb_list = lbs.load_balancers or []

            #     if not old_lbs:
            #         return (True, bool(lb_list))

            #     old_lb_list = old_lbs.load_balancers or []
            #     old_target_group_arn_to_lb: dict[str, AwsApplicationLoadBalancer] = {}
            #     for old_lb in old_lb_list:
            #         if old_lb.target_group_arn:
            #             old_target_group_arn_to_lb[old_lb.target_group_arn] = old_lb

            #     for lb in lb_list:
            #         if not lb.target_group_arn:
            #             continue

            #         old_lb_2 = old_target_group_arn_to_lb.pop(lb.target_group_arn, None)

            #         if old_lb_2:
            #             if (old_lb_2.container_name != lb.container_name) or \
            #                     (old_lb_2.container_port != lb.container_port):
            #                 logger.info(f"Found different details for target group ARN: '{lb.target_group_arn}': {lb}")
            #                 return (True, True)
            #         else:
            #             logger.info(f"Found new target group ARN: '{lb.target_group_arn}', must recreate service")
            #             return (True, True)

            #     if bool(old_target_group_arn_to_lb) or \
            #             (old_lbs.health_check_grace_period_seconds != lbs.health_check_grace_period_seconds):
            #         return (True, True)
            # elif old_lbs:
            #     return (True, True)

            # recreate is False from here down

            if (old_task.service_instance_count != task.service_instance_count) or \
                    (old_settings.task_definition_arn != self.settings.task_definition_arn) or \
                    (old_aws_ecs_execution_method.compute_tags() != self.compute_tags()):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} Task settings changed, update required, but not recreate (1)")
                return (True, False)

            network = self.aws_settings.network

            if (not network) or (not network.subnets):
                raise APIException("Missing network settings for service")

            if (not old_network.subnets) or (set(old_network.subnets) != set(network.subnets)):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} subnets have changed from {old_network.subnets} to {network.subnets}, update required but not recreate")
                return (True, False)

            if set(network.security_groups or []) != set(old_network.security_groups or []):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} security groups have changed from {old_network.security_groups} to {network.security_groups}, update required but not recreate")
                return (True, False)

            if ss:
                if (old_ss.enable_ecs_managed_tags != ss.enable_ecs_managed_tags) or \
                    (old_ss.propagate_tags != ss.propagate_tags):
                    logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} service settings changed, update required, but not recreate (3)")
                    return (True, False)

                dc = ss.deployment_configuration
                old_dc = old_ss.deployment_configuration

                if dc and (dc != old_dc):
                    logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {dc=} != {old_dc=}, requires update but no recreate (2)")
                    return (True, False)
        except Exception:
            logger.warning(f"Can't parse old Task service settings: {task.uuid=} {old_ss}", exc_info=True)
            return (True, True)

        logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} no update or recreate required")

        return (False, False)

    def setup_service(self, old_execution_method: Optional['ExecutionMethod']=None,
            force_creation: bool=False, teardown_result: Optional[Any]=None) -> None:
        task = self.task

        if not task:
            raise RuntimeError("No Task found")

        ss = self.service_settings

        if not ss:
            raise RuntimeError("No service settings found")

        logger.info(f"setup_service() for Task {task.name}, {force_creation=}, {teardown_result=} ...")

        old_aws_ecs_execution_method: Optional[AwsEcsExecutionMethod] = None
        old_ecs_client: Optional[Any] = None
        existing_service_info: Optional[AwsEcsServiceResponseFragment] = None
        aws_ecs_service_teardown_result: Optional[AwsEcsServiceTeardownResult] = None

        if isinstance(old_execution_method, AwsEcsExecutionMethod):
            old_aws_ecs_execution_method = cast(AwsEcsExecutionMethod, old_execution_method)

            if teardown_result:
                aws_ecs_service_teardown_result = cast(AwsEcsServiceTeardownResult, teardown_result)
                existing_service_info = aws_ecs_service_teardown_result.service_info
                logger.info(f"setup_service(): {task.uuid} got {existing_service_info=} from teardown result")

        if (existing_service_info is None) and old_aws_ecs_execution_method:
            old_service_settings = old_aws_ecs_execution_method.service_settings
            old_service_arn: Optional[str] = None

            if old_service_settings:
                old_service_arn = old_service_settings.service_arn
                logger.info(f"setup_service(): {task.uuid} found {old_service_arn=}")
            else:
                logger.info(f"setup_service(): {task.uuid} old_service_arn not found")

            try:
                old_ecs_client = old_aws_ecs_execution_method.make_ecs_client()
                existing_service_info = old_aws_ecs_execution_method.find_aws_ecs_service(
                        ecs_client=old_ecs_client, service_arn_or_name=old_service_arn)
            except Exception:
                logger.warning("Cannot find existing ECS service with old execution method")

        ecs_client: Optional[Any] = None

        if not existing_service_info:
            ecs_client = self.make_ecs_client()
            existing_service_info = self.find_aws_ecs_service(ecs_client=ecs_client,
                    service_arn_or_name=ss.service_arn)

        # When creating a service that specifies multiple target groups, the Amazon ECS service-linked role must be created. The role is created by omitting the role parameter in API requests, or the Role property in AWS CloudFormation. For more information, see Service-Linked Role for Amazon ECS.
        #role = task.aws_ecs_default_task_role or task.aws_ecs_default_execution_role or \
        #    run_env.aws_ecs_default_task_role or run_env.aws_ecs_default_execution_role

        service_name: Optional[str] = None
        if existing_service_info:
            service_name = existing_service_info.service_name

            logger.info(f"setup_service() for Task {task.uuid} found existing service {service_name}")
            if force_creation and (existing_service_info.last_status == 'ACTIVE'):
                if old_aws_ecs_execution_method:
                    logger.info(f"setup_service(): deleting ACTIVE service {service_name} ...")
                    old_ecs_client = old_ecs_client or old_aws_ecs_execution_method.make_ecs_client()
                    existing_service_info = old_aws_ecs_execution_method.delete_service(
                            service_name=service_name, ecs_client=old_ecs_client)
                else:
                    logger.warning(f"setup_service(): {task.uuid} service {service_name} existed before Task was saved as an AWS ECS Task?")
                    # TODO: how to recover?
            else:
                logger.info(f"setup_service() {task.uuid} not deleting existing service {service_name}")

        if (existing_service_info is None) or \
                (existing_service_info.last_status == 'INACTIVE'):
            logger.info(f"Clearing service_arn for inactive or missing service {service_name or 'N/A'}")

            # TODO: remove when Task.service_settings is the source of truth
            task.aws_ecs_service_arn = ''

            # TODO: set generic service_updated_at column
            task.aws_ecs_service_updated_at = timezone.now()

            ss.service_arn = None
            task.service_settings = ss.dict()

            # Can't save if this is part of a creation request
            if task.pk:
                task.save_without_sync()

        load_balancer_settings = ss.load_balancer_settings
        ecs_client = ecs_client or self.make_ecs_client()

        if (not force_creation) and existing_service_info and \
                (existing_service_info.last_status == 'ACTIVE'):
            logger.info(f"setup_service() for Task {task.name} updating service ...")

            args = self.make_common_service_args(include_launch_type=False)
            args['service'] = service_name
            args['forceNewDeployment'] = ss.force_new_deployment or False

            if load_balancer_settings and load_balancer_settings.load_balancers:
                args['healthCheckGracePeriodSeconds'] = \
                    load_balancer_settings.health_check_grace_period_seconds or \
                    self.DEFAULT_LOAD_BALANCER_HEALTH_CHECK_GRACE_PERIOD_SECONDS

            response = ecs_client.update_service(**args)
        else:
            args = self.add_creation_args(self.make_common_service_args(
                    include_launch_type=True))

            if service_name is None:
                new_service_name = self.make_aws_ecs_service_name()
            elif existing_service_info:
                new_service_name = self.make_aws_ecs_service_name(
                        index=existing_service_info.next_service_name_suffix or 0)

            logger.info(f"setup_service() for Task {task.name} creating service with {new_service_name=} ...")

            args['serviceName'] = new_service_name

            client_token = ''.join(random.choice(string.ascii_letters) for i in range(30))
            args['clientToken'] = client_token
            args['schedulingStrategy'] = ss.scheduling_strategy or 'REPLICA'
            args['deploymentController'] = {
                'type': 'ECS'
            }

            if load_balancer_settings and load_balancer_settings.load_balancers:
                load_balancer_dicts = []
                for lb_setting in load_balancer_settings.load_balancers:
                    load_balancer_dict = {
                        'targetGroupArn': lb_setting.target_group_arn,
                        'containerName': lb_setting.container_name or self.settings.main_container_name,
                        'containerPort': lb_setting.container_port
                    }
                    load_balancer_dicts.append(load_balancer_dict)

                args['loadBalancers'] = load_balancer_dicts

                if len(load_balancer_dicts) > 0:
                    args['healthCheckGracePeriodSeconds'] = \
                        load_balancer_settings.health_check_grace_period_seconds or \
                        self.DEFAULT_LOAD_BALANCER_HEALTH_CHECK_GRACE_PERIOD_SECONDS

            if ss.enable_ecs_managed_tags is not None:
                args['enableECSManagedTags'] = ss.enable_ecs_managed_tags

            if ss.propagate_tags:
                args['propagateTags'] = ss.propagate_tags

            response = ecs_client.create_service(**args)

        service_info = AwsEcsServiceResponseFragment.from_boto_service_response_fragment(
                service_dict=response['service'])

        # TODO: Remove when Task.service_settings are the source of truth
        task.aws_ecs_service_arn = service_info.service_arn
        task.aws_ecs_service_updated_at = timezone.now()

        ss.service_arn = service_info.service_arn
        task.service_settings = ss.dict()

        logger.info(f"setup_service() for Task {task.name} got service ARN {ss.service_arn} ...")


    def teardown_service(self) -> Tuple[Optional[dict[str, Any]], Optional[Any]]:
        task = self.task

        if not task:
            raise RuntimeError("teardown_service(): No Task found")

        logger.info(f"Tearing down service for Task {task.name} ...")

        teardown_result = AwsEcsServiceTeardownResult()
        ssd: Optional[dict[str, Any]] = None

        ecs_client = self.make_ecs_client()
        existing_service_info = self.find_aws_ecs_service(ecs_client=ecs_client)

        if existing_service_info and self.settings.cluster_arn:
            # TODO: Mark Task Executions as STOPPED so they are aborted the next
            # time they heartbeat

            service_name = existing_service_info.service_name
            service_info = self.delete_service(
                    service_name=service_name,
                    ecs_client=ecs_client)

            teardown_result.service_info = service_info

            if service_info.last_status == 'INACTIVE':
                logger.info(f'Service {service_name} was inactive, clearing service ARN')

                # TODO: Remove when service_settings are the source of truth
                task.aws_ecs_service_arn = ''

                if self.service_settings:
                    self.service_settings.service_arn = None
                    ssd = self.service_settings.dict()
                    task.service_settings = ssd
            else:
                logger.info(f'Service {service_name} had status {service_info.last_status}, saving service ARN')

                # The service ARN is not modified so that the name can be
                # incremented next time the service is enabled.
                service_arn = service_info.service_arn

                # TODO: Remove when service_settings are the source of truth
                task.aws_ecs_service_arn = service_arn

                if self.service_settings:
                    self.service_settings.service_arn = service_arn
                else:
                    self.service_settings = AwsEcsServiceSettings.from_boto_service_response_fragment(
                            service_dict=service_info.service_dict)

                ssd = self.service_settings.dict()
                task.service_settings = ssd

            task.aws_ecs_service_updated_at = timezone.now()
        else:
            logger.info(f"Tearing down service for Task {task.name} was a no-op since service was not found")

            # TODO: Remove when service_settings are the source of truth
            task.aws_ecs_service_arn = ''

            if self.service_settings:
                self.service_settings.service_arn = None
                ssd = self.service_settings.dict()

        return (ssd, teardown_result)

    def manually_start(self) -> None:
        task_execution = self.task_execution

        if task_execution is None:
            raise APIException("No Task Execution found")

        task = self.task

        if task is None:
            raise APIException("No Task found")

        if task_execution.is_service is None:
            task_execution.is_service = task.is_service

        task_execution.heartbeat_interval_seconds = task_execution.heartbeat_interval_seconds or task.heartbeat_interval_seconds
        task_execution.task_max_concurrency = task_execution.task_max_concurrency or task.max_concurrency
        task_execution.max_conflicting_age_seconds = task_execution.max_conflicting_age_seconds or task.max_age_seconds

        if task_execution.process_max_retries is None:
            task_execution.process_max_retries = task.default_max_retries

        args = self.add_creation_args(self.make_common_args(
                include_launch_type=True))
        cpu_units = task_execution.allocated_cpu_units \
                or task.allocated_cpu_units or self.DEFAULT_CPU_UNITS
        memory_mb = task_execution.allocated_memory_mb \
                or task.allocated_memory_mb or self.DEFAULT_MEMORY_MB

        flattened_environment = make_flattened_environment(env=task_execution.make_environment())

        logger.info(f"manually_start() with args = {args}, " +
            f"{cpu_units=}, {memory_mb=}, " +
            f"{self.settings.execution_role_arn=}, {self.settings.task_role_arn=}")

        # TODO: Remove when execution_method_details are the source of truth
        task_execution.aws_ecs_cluster_arn = args['cluster']
        task_execution.aws_ecs_task_definition_arn = args['taskDefinition']
        task_execution.aws_ecs_platform_version = args['platformVersion']
        task_execution.aws_ecs_launch_type = args['launchType']
        task_execution.aws_ecs_execution_role = self.settings.execution_role_arn or ''
        task_execution.aws_ecs_task_role = self.settings.task_role_arn or ''
        nc = args['networkConfiguration']['awsvpcConfiguration']
        task_execution.aws_subnets = nc['subnets']
        task_execution.aws_ecs_security_groups = nc['securityGroups']
        task_execution.aws_ecs_assign_public_ip = \
                (nc['assignPublicIp'] == 'ENABLED')

        task_execution.allocated_cpu_units = cpu_units
        task_execution.allocated_memory_mb = memory_mb

        aws_ecs_settings = AwsEcsExecutionMethodInfo.parse_obj(
            task_execution.execution_method_details or {})
        aws_ecs_settings.cluster_arn = self.settings.cluster_arn
        aws_ecs_settings.task_definition_arn = self.settings.task_definition_arn
        aws_ecs_settings.platform_version = self.settings.platform_version
        aws_ecs_settings.launch_type = self.settings.launch_type
        aws_ecs_settings.execution_role_arn = self.settings.execution_role_arn
        aws_ecs_settings.task_role_arn = self.settings.task_role_arn

        task_execution.execution_method_type = self.NAME
        task_execution.execution_method_details = aws_ecs_settings.dict()

        aws_settings = AwsSettings.parse_obj(task_execution.infrastructure_settings or {})
        network = aws_settings.network

        if network is None:
            network = AwsNetworkSettings()
            aws_settings.network = network

        merged_network = self.aws_settings.network

        if merged_network is None:
            merged_network = AwsNetworkSettings()

        network.subnets = merged_network.subnets
        network.security_groups = merged_network.security_groups
        network.assign_public_ip = merged_network.assign_public_ip

        task_execution.infrastructure_type = INFRASTRUCTURE_TYPE_AWS
        task_execution.infrastructure_settings = aws_settings.dict()

        task_execution.save()
        task.latest_task_execution = task_execution
        task.save_without_sync()

        success = False
        try:
            ecs_client = self.aws_settings.make_boto3_client('ecs',
                    session_uuid=str(task_execution.uuid))

            overrides = {
                'containerOverrides': [
                    {
                        'name': self.settings.main_container_name,
#                        'command': [
#                            'string',
#                        ],
                        'environment': flattened_environment,
                        'cpu': cpu_units,
                        'memory': memory_mb,
#                        'memoryReservation': task_execution.allocated_memory_mb or task.allocated_memory_mb,
#                        'resourceRequirements': [
#                            {
#                                'value': 'string',
#                                'type': 'GPU'
#                            },
#                       ]
                    },
                ],
                'executionRoleArn': self.settings.execution_role_arn,
            }

            if self.settings.task_role_arn:
                overrides['taskRoleArn'] = self.settings.task_role_arn

            args.update({
              'overrides': overrides,
              'count': 1,
              'startedBy': 'CloudReactor',
              # group='string',
              # placementConstraints=[
              #     {
              #         'type': 'distinctInstance' | 'memberOf',
              #         'expression': 'string'
              #     },
              # ],
              # placementStrategy=[
              #     {
              #         'type': 'random' | 'spread' | 'binpack',
              #         'field': 'string'
              #     },
              # ],
            })

            if self.settings.enable_ecs_managed_tags is not None:
                args['enableECSManagedTags'] = self.settings.enable_ecs_managed_tags

            if self.settings.propagate_tags:
                args['propagateTags'] = self.settings.propagate_tags

            if self.settings.enable_execute_command is not None:
                args['enableExecuteCommand'] = self.settings.enable_execute_command

            if self.settings.task_group:
                args['group'] = self.settings.task_group

            rv = ecs_client.run_task(**args)

            logger.info(f"Got run_task() return value {rv}")

            # TODO: handle failures in rv['failures'][]

            # TODO: remove once execution_method_details is the source of truth
            task_execution.aws_ecs_task_arn = rv['tasks'][0]['taskArn']

            task_arn = rv['tasks'][0]['taskArn']
            cast(AwsEcsExecutionMethodInfo, self.settings).task_arn = task_arn
            task_execution.execution_method_details['task_arn'] = task_arn
            task_execution.error_details = None

            success = True
        except ClientError as client_error:
            logger.warning(f'Failed to start Task {task.uuid}', exc_info=True)
            task_execution.error_details = client_error.response
        except Exception as ex:
            logger.warning(f'Failed to start Task {task.uuid}', exc_info=True)
            task_execution.error_details = {
                'exception': str(ex)
            }

        if not success:
            from ..models import TaskExecution
            task_execution.status = TaskExecution.Status.FAILED
            task_execution.stop_reason = TaskExecution.StopReason.FAILED_TO_START
            task_execution.finished_at = timezone.now()

        task_execution.save()

    def make_aws_ecs_service_name(self, index: int = 0) -> str:
        if not self.task:
            raise APIException("make_aws_ecs_service_name(): missing Task")

        return 'CR_' + str(self.task.uuid) + '_' + str(index)

    def find_aws_ecs_service(self, ecs_client: Optional[Any]=None,
            service_arn_or_name: Optional[str] = None) -> Optional[AwsEcsServiceResponseFragment]:
        if ecs_client is None:
            ecs_client = self.make_ecs_client()

        cluster = self.settings.cluster_arn

        if not cluster:
            logger.debug("find_aws_ecs_service(): No ECS Cluster found, returning None")
            return None

        if not service_arn_or_name:
            if self.service_settings:
                service_arn_or_name = self.service_settings.service_arn

            service_arn_or_name = service_arn_or_name or self.make_aws_ecs_service_name()

        logger.debug(f"describe_services() with {service_arn_or_name=}, {cluster=}")

        try:
            response_dict = ecs_client.describe_services(
                cluster=cluster,
                services=[service_arn_or_name])
            services = response_dict['services']

            if len(services) == 0:
                logger.info(f"No service named '{service_arn_or_name}' found for cluster '{cluster}'")
                return None

            return AwsEcsServiceResponseFragment.from_boto_service_response_fragment(
                    services[0])
        except Exception:
            logger.warning("Can't describe services", exc_info=True)
            return None

    def make_ecs_client(self):
        session_id = ''

        if self.task:
            if self.task.uuid:
                session_id = str(self.task.uuid)
            else:
                session_id = str(self.task.run_environment.uuid)
        else:
            session_id = str(uuid.uuid4())

        return self.aws_settings.make_boto3_client('ecs',
              session_uuid=session_id)

    def delete_service(self, service_name: str, ecs_client: Any) -> AwsEcsServiceResponseFragment:
        logger.info(f"Deleting service '{service_name}' ...")
        deletion_response = ecs_client.delete_service(
            cluster=self.settings.cluster_arn,
            service=service_name,
            force=True)

        return AwsEcsServiceResponseFragment.from_boto_service_response_fragment(
                deletion_response['service'])

    def assign_public_ip_str(self) -> str:
        aws_network = self.aws_settings.network

        assign_public_ip = False

        if aws_network and aws_network.assign_public_ip:
            assign_public_ip = True

        if assign_public_ip:
            return 'ENABLED'

        return 'DISABLED'

    def make_common_args(self, include_launch_type: bool=True) -> dict[str, Any]:
        from ..models.aws_ecs_configuration import AwsEcsConfiguration

        platform_version = self.settings.platform_version \
                or AwsEcsConfiguration.PLATFORM_VERSION_LATEST

        subnets: list[str] = []
        security_groups: list[str] = []

        task_network = self.aws_settings.network

        if task_network:
            subnets = task_network.subnets or subnets
            security_groups = task_network.security_groups or security_groups

        # TODO: check if empty subnets is viable

        assign_public_ip = self.assign_public_ip_str()
        args = {
            'cluster': self.settings.cluster_arn,
            'taskDefinition': self.settings.task_definition_arn,
            'networkConfiguration': {
                'awsvpcConfiguration': {
                    'subnets': subnets,
                    'securityGroups': security_groups,
                    'assignPublicIp': assign_public_ip
                }
            },
            'platformVersion': platform_version,
        }

        if include_launch_type:
            launch_type = self.settings.launch_type or self.DEFAULT_LAUNCH_TYPE

            if (self.settings.supported_launch_types is not None) and \
                (launch_type not in self.settings.supported_launch_types):
                raise APIException(f"Launch type '{launch_type}' is not supported")

            args['launchType'] = launch_type

        return args


    def make_common_service_args(self, include_launch_type: bool=True) \
            -> dict[str, Any]:
        ss = self.service_settings

        if not ss:
            raise RuntimeError('No service settings found')

        task = self.task

        if not task:
            raise RuntimeError('No Task found')

        args = self.make_common_args(include_launch_type=include_launch_type)
        args['desiredCount'] = task.service_instance_count

        managed_tags = ss.enable_ecs_managed_tags
        if managed_tags is not None:
            args['enableECSManagedTags'] = managed_tags

        dc = ss.deployment_configuration or AwsEcsServiceDeploymentConfiguration()
        dcb = dc.deployment_circuit_breaker or AwsEcsServiceDeploymentCircuitBreaker()

        args['deploymentConfiguration'] = {
            'maximumPercent': coalesce(dc.maximum_percent, 200),
            'minimumHealthyPercent': coalesce(dc.minimum_healthy_percent, 100),
            'deploymentCircuitBreaker': {
                'enable': coalesce(dcb.enable, False),
                'rollback': coalesce(dcb.rollback_on_failure, False),
            }
        }

        return args

    def add_creation_args(self, args: dict[str, Any]) -> dict[str, Any]:
        tags = self.compute_tags()

        if len(tags) > 0:
            args['tags']  = [
                { 'key': k, 'value': v } for k, v in tags.items() if v
            ][0:self.MAX_TAG_COUNT]

        # TODO:
        # serviceRegistries=[
        #     {
        #         'registryArn': 'string',
        #         'port': 123,
        #         'containerName': 'string',
        #         'containerPort': 123
        #     },
        # ],

        return args

    def compute_tags(self) -> dict[str, str]:
        tags = (self.aws_settings.tags or {}).copy()

        if self.service_settings and self.service_settings.tags:
            tags |= self.service_settings.tags

        output_tags: dict[str, str] = {}

        for k, v in tags.items():
            # Ignore empty values
            if v and (v != '__UNSET__'):
                output_tags[k] = v

        return output_tags

    def enrich_task_settings(self) -> None:
        if not self.task:
            raise RuntimeError("No Task found")

        super().enrich_task_settings()

        emcd = self.task.execution_method_capability_details
        if emcd:
            aws_ecs_settings = AwsEcsExecutionMethodSettings.parse_obj(emcd)
            aws_ecs_settings.update_derived_attrs(aws_settings=self.aws_settings)
            self.task.execution_method_capability_details = aws_ecs_settings.dict()

        if self.service_settings:
            self.service_settings.update_derived_attrs(task=self.task,
                    aws_ecs_settings=self.settings,
                    aws_settings=self.aws_settings)
            self.task.service_settings = deepmerge(self.task.service_settings,
                    self.service_settings.dict())

    def enrich_task_execution_settings(self) -> None:
        if self.task_execution is None:
            raise APIException("enrich_task_settings(): Missing Task Execution")

        super().enrich_task_execution_settings()

        emd = self.task_execution.execution_method_details

        if emd:
            aws_ecs_settings =  AwsEcsExecutionMethodInfo.parse_obj(emd)
            aws_ecs_settings.update_derived_attrs(aws_settings=self.aws_settings)

            self.task_execution.execution_method_details = deepmerge(
                    emd, aws_ecs_settings.dict())
