from typing import Any, FrozenSet, TYPE_CHECKING

import logging
import random
import string

from django.utils import timezone

from rest_framework.exceptions import APIException

from botocore.exceptions import ClientError

from ..common.aws import *

if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )

from .execution_method import ExecutionMethod

logger = logging.getLogger(__name__)


class AwsEcsExecutionMethod(ExecutionMethod):
    NAME = 'AWS ECS'

    LAUNCH_TYPE_EC2 = 'EC2'
    LAUNCH_TYPE_FARGATE = 'FARGATE'
    ALL_LAUNCH_TYPES = [LAUNCH_TYPE_FARGATE, LAUNCH_TYPE_EC2]
    DEFAULT_LAUNCH_TYPE = LAUNCH_TYPE_FARGATE
    DEFAULT_CPU_UNITS = 256
    DEFAULT_MEMORY_MB = 512

    SERVICE_PROPAGATE_TAGS_TASK_DEFINITION = 'TASK_DEFINITION'
    SERVICE_PROPAGATE_TAGS_SERVICE = 'SERVICE'

    SERVICE_PROPAGATE_TAGS_CHOICES = [
        SERVICE_PROPAGATE_TAGS_TASK_DEFINITION,
        SERVICE_PROPAGATE_TAGS_SERVICE,
    ]

    CAPABILITIES_WITH_SCHEDULING = frozenset([
        ExecutionMethod.ExecutionCapability.MANUAL_START,
        ExecutionMethod.ExecutionCapability.SETUP_SERVICE
    ])

    MAX_TAG_COUNT = 50

    def __init__(self, task: 'Task'):
        super().__init__(self.NAME, task)

    def capabilities(self) -> FrozenSet[ExecutionMethod.ExecutionCapability]:
        task = self.task
        run_env = task.run_environment

        if not run_env.can_control_aws_ecs():
            return frozenset()

        execution_role = task.aws_ecs_default_execution_role or \
            run_env.aws_ecs_default_execution_role

        if not execution_role:
            return frozenset()

        cluster_arn = task.aws_ecs_default_cluster_arn or \
            run_env.aws_ecs_default_cluster_arn

        if not cluster_arn:
            return frozenset()

        subnets = task.aws_default_subnets or run_env.aws_default_subnets
        if not subnets:
            return frozenset()

        security_groups = task.aws_ecs_default_security_groups or \
                run_env.aws_ecs_default_security_groups

        if not security_groups:
            return frozenset()

        if run_env.aws_events_role_arn:
            return ExecutionMethod.ALL_CAPABILITIES

        return self.CAPABILITIES_WITH_SCHEDULING


    def setup_scheduled_execution(self) -> None:
        task = self.task

        if not task.schedule.startswith('cron') and not task.schedule.startswith('rate'):
            raise APIException(detail=f"Schedule '{task.schedule}' is invalid")

        aws_scheduled_execution_rule_name = f"CR_{task.uuid}"

        client = self.make_events_client()

        state = 'ENABLED' if task.enabled else 'DISABLED'

        run_env = task.run_environment

        execution_role_arn = task.aws_ecs_default_execution_role or run_env.aws_ecs_default_execution_role

        logger.info(f"Using execution role arn = '{execution_role_arn}'")

        # Need this permission: https://github.com/Miserlou/Zappa/issues/381
        response = client.put_rule(
            Name=aws_scheduled_execution_rule_name,
            ScheduleExpression=task.schedule,
            #EventPattern='true',
            State=state,
            Description=f"Scheduled execution of Task '{task.name}' ({task.uuid})",
            RoleArn=execution_role_arn
        )
            # TODO: use add_creation_args()
            # Tags=[
            #     {
            #         'Key': 'string',
            #         'Value': 'string'
            #     },
            # ],
            # EventBusName='string'

        task.aws_scheduled_execution_rule_name = aws_scheduled_execution_rule_name
        task.aws_scheduled_event_rule_arn = response['RuleArn']

        logger.info(f"got rule ARN = {task.aws_scheduled_event_rule_arn}")

        if task.enabled:
            client.enable_rule(Name=aws_scheduled_execution_rule_name)
        else:
            client.disable_rule(Name=aws_scheduled_execution_rule_name)

        aws_event_target_rule_name = f"CR_{task.uuid}"
        aws_event_target_id = f"CR_{task.uuid}"
        cluster_arn = task.aws_ecs_default_cluster_arn or run_env.aws_ecs_default_cluster_arn
        launch_type = task.aws_ecs_default_launch_type or run_env.aws_ecs_default_launch_type
        platform_version = task.aws_ecs_default_platform_version or \
                run_env.aws_ecs_default_platform_version or \
                AWS_ECS_PLATFORM_VERSION_LATEST
        subnets = task.aws_default_subnets or run_env.aws_default_subnets
        security_groups = task.aws_ecs_default_security_groups or run_env.aws_ecs_default_security_groups
        assign_public_ip = self.assign_public_ip_str()

        response = client.put_targets(
            Rule=aws_event_target_rule_name,
            Targets=[
                {
                    'Id': aws_event_target_id,
                    'Arn': cluster_arn,
                    'RoleArn': run_env.aws_events_role_arn,
                    'EcsParameters': {
                        'TaskDefinitionArn': task.aws_ecs_task_definition_arn,
                        'TaskCount': task.scheduled_instance_count or 1,
                        'LaunchType': launch_type,
                        # Only for tasks that use awsvpc networking
                        'NetworkConfiguration': {
                            'awsvpcConfiguration': {
                                'Subnets': subnets,
                                'SecurityGroups': security_groups,
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

        task.aws_event_target_rule_name = aws_event_target_rule_name
        task.aws_event_target_id = aws_event_target_id

    def teardown_scheduled_execution(self) -> None:
        client = None
        task = self.task

        if task.aws_event_target_rule_name and task.aws_event_target_id:
            client = self.make_events_client()

            try:
                response = client.remove_targets(
                    Rule=task.aws_event_target_rule_name,
                    #EventBusName='string',
                    Ids=[
                        task.aws_event_target_id
                    ],
                    Force=False
                )
                handle_aws_multiple_failure_response(response)
                task.aws_event_target_rule_name = ''
                task.aws_event_target_id = ''
            except ClientError as client_error:
                error_code = client_error.response['Error']['Code']
                # Happens if the schedule rule is removed manually
                if error_code == 'ResourceNotFoundException':
                    logger.warning(f"teardown_scheduled_execution(): Can't remove target {task.aws_event_target_rule_name} because resource not found, exception = {client_error}")
                else:
                    logger.exception(f"teardown_scheduled_execution(): Can't remove target {task.aws_event_target_rule_name} due to unhandled error {error_code}")
                    raise client_error

        if task.aws_scheduled_execution_rule_name:
            client = client or self.make_events_client()

            try:
                client.delete_rule(
                    Name=task.aws_scheduled_execution_rule_name,
                    #EventBusName='string'
                    Force=True
                )
            except ClientError as client_error:
                error_code = client_error.response['Error']['Code']
                # Happens if the schedule rule is removed manually
                if error_code == 'ResourceNotFoundException':
                    logger.warning(
                        f"teardown_scheduled_execution(): Can't disable rule{task.aws_scheduled_execution_rule_name} because resource not found, exception = {client_error}")
                else:
                    logger.exception(
                        f"teardown_scheduled_execution(): Can't remove target {task.aws_scheduled_execution_rule_name} due to unhandled error {error_code}")
                    raise client_error

            task.aws_scheduled_event_rule_arn = ''

    def setup_service(self, force_creation=False):
        from ..models.task import Task

        task = self.task
        run_env = task.run_environment
        ecs_client = run_env.make_boto3_client('ecs')

        existing_service = self.find_aws_ecs_service(ecs_client=ecs_client)

        if existing_service:
            service_name = existing_service['serviceName']
        else:
            service_name = self.make_aws_ecs_service_name()


        # When creating a service that specifies multiple target groups, the Amazon ECS service-linked role must be created. The role is created by omitting the role parameter in API requests, or the Role property in AWS CloudFormation. For more information, see Service-Linked Role for Amazon ECS.
        #role = task.aws_ecs_default_task_role or task.aws_ecs_default_execution_role or \
        #    run_env.aws_ecs_default_task_role or run_env.aws_ecs_default_execution_role

        new_service_name = service_name
        if existing_service:
            current_status = existing_service['status'].upper()
            if force_creation or (current_status != 'ACTIVE'):
                logger.info(f"Deleting service '{service_name}' before updating ...")
                cluster = task.aws_ecs_default_cluster_arn or run_env.aws_ecs_default_cluster_arn
                deletion_response = ecs_client.delete_service(
                    cluster=cluster,
                    service=service_name,
                    force=True)

                deleted_service = deletion_response['service']
                current_status = deleted_service['status'].upper()

                if current_status in ('DRAINING', 'ACTIVE'):
                    service_name = deleted_service['serviceName']

                    logger.info(f"Current status of service '{service_name}' is {current_status}, will change service name")
                    m = Task.SERVICE_NAME_REGEX.match(service_name)

                    if m:
                        index_str = m.group(3)
                        if index_str:
                            new_service_name = self.make_aws_ecs_service_name(int(index_str) + 1)
                        else:
                            new_service_name = self.make_aws_ecs_service_name()

                        logger.info(f"Parsed service name '{service_name}', will use '{new_service_name}' as new service name")
                    else:
                        new_service_name = self.make_aws_ecs_service_name()
                        logger.warning(f"Can't match service name '{service_name}', will use '{new_service_name}' as new service name")

                existing_service = None
                task.aws_ecs_service_arn = ''
                task.aws_ecs_service_updated_at = timezone.now()

        if existing_service:
            args = self.make_common_service_args(include_launch_type=False)
            args['service'] = service_name
            args['forceNewDeployment'] = \
                task.aws_ecs_service_force_new_deployment or False

            if task.aws_ecs_service_load_balancer_details_set.count() > 0:
                args['healthCheckGracePeriodSeconds'] = \
                    task.aws_ecs_service_load_balancer_health_check_grace_period_seconds or \
                            Task.DEFAULT_ECS_SERVICE_LOAD_BALANCER_HEALTH_CHECK_GRACE_PERIOD_SECONDS

            response = ecs_client.update_service(**args)
        else:
            args = self.add_creation_args(self.make_common_service_args(
                    include_launch_type=True))
            args['serviceName'] = service_name

            client_token = ''.join(random.choice(string.ascii_letters) for i in range(30))
            args['clientToken'] = client_token
            args['schedulingStrategy'] = 'REPLICA'
            args['deploymentController'] = {
                'type': 'ECS'
            }

            load_balancers = []
            for load_balancer in task.aws_ecs_service_load_balancer_details_set.all():
                load_balancer_dict = {
                    'targetGroupArn': load_balancer.target_group_arn,
                    'containerName': load_balancer.container_name or task.aws_ecs_main_container_name,
                    'containerPort': load_balancer.container_port
                }
                load_balancers.append(load_balancer_dict)

            args['loadBalancers'] = load_balancers

            if task.aws_ecs_service_load_balancer_details_set.count() > 0:
                args['healthCheckGracePeriodSeconds'] = \
                    task.aws_ecs_service_load_balancer_health_check_grace_period_seconds or \
                    task.DEFAULT_ECS_SERVICE_LOAD_BALANCER_HEALTH_CHECK_GRACE_PERIOD_SECONDS

            if task.aws_ecs_service_enable_ecs_managed_tags is not None:
                args['enableECSManagedTags'] = task.aws_ecs_service_enable_ecs_managed_tags

            if task.aws_ecs_service_propagate_tags:
                args['propagateTags'] = task.aws_ecs_service_propagate_tags

            response = ecs_client.create_service(**args)

        task.aws_ecs_service_arn = response['service']['serviceArn']
        task.aws_ecs_service_updated_at = timezone.now()
        return response

    def teardown_service(self) -> None:
        task = self.task
        run_env = task.run_environment
        ecs_client = run_env.make_boto3_client('ecs')
        existing_service = self.find_aws_ecs_service(ecs_client=ecs_client)
        cluster = task.aws_ecs_default_cluster_arn or run_env.aws_ecs_default_cluster_arn

        if existing_service:
            service_name = existing_service['serviceName']
            deletion_response = ecs_client.delete_service(
                cluster=cluster,
                service=service_name,
                force=True)

            deleted_service = deletion_response['service']
            current_status = deleted_service['status'].upper()

            if current_status == 'INACTIVE':
                logger.info(f'Service {service_name} was inactive, clearing service ARN')
                task.aws_ecs_service_arn = ''
            else:
                logger.info(f'Service {service_name} had status {current_status}, saving service ARN')
                # The service ARN is not modified so that the name can be
                # incremented next time the service is enabled.
                task.aws_ecs_service_arn = deleted_service['serviceArn']

            task.aws_ecs_service_updated_at = timezone.now()

            # TODO: Mark Task Executions as STOPPED so they are aborted the next
            # time they heartbeat

    def manually_start(self, task_execution: 'TaskExecution'):
        task = task_execution.task

        if task_execution.is_service is None:
            task_execution.is_service = task.is_service

        task_execution.heartbeat_interval_seconds = task_execution.heartbeat_interval_seconds or task.heartbeat_interval_seconds
        task_execution.task_max_concurrency = task_execution.task_max_concurrency or task.max_concurrency
        task_execution.max_conflicting_age_seconds = task_execution.max_conflicting_age_seconds or task.max_age_seconds

        if task_execution.process_max_retries is None:
            task_execution.process_max_retries = task.default_max_retries

        run_env = task.run_environment

        args = self.add_creation_args(self.make_common_args(
                include_launch_type=True, task_execution=task_execution),
                task_execution=task_execution)
        cpu_units = task_execution.allocated_cpu_units \
                or task.allocated_cpu_units or self.DEFAULT_CPU_UNITS
        memory_mb = task_execution.allocated_memory_mb \
                or task.allocated_memory_mb or self.DEFAULT_MEMORY_MB

        execution_role_arn = task_execution.aws_ecs_execution_role \
                or task.aws_ecs_default_execution_role \
                or run_env.aws_ecs_default_execution_role
        task_role_arn = task_execution.aws_ecs_task_role \
                or task.aws_ecs_default_task_role \
                or run_env.aws_ecs_default_task_role

        environment = task_execution.make_environment()
        flattened_environment = []
        for name, value in environment.items():
            flattened_environment.append({
                'name': name,
                'value': value
            })

        logger.info(f"manually_start() with args = {args}, " +
            f"{cpu_units=}, {memory_mb=}, " +
            f"{execution_role_arn=}, {task_role_arn=}")

        task_execution.aws_ecs_cluster_arn = args['cluster']
        task_execution.aws_ecs_task_definition_arn = args['taskDefinition']
        task_execution.aws_ecs_platform_version = args['platformVersion']
        task_execution.allocated_cpu_units = cpu_units
        task_execution.allocated_memory_mb = memory_mb
        task_execution.aws_ecs_launch_type = args['launchType']
        task_execution.aws_ecs_execution_role = execution_role_arn
        task_execution.aws_ecs_task_role = task_role_arn

        nc = args['networkConfiguration']['awsvpcConfiguration']
        task_execution.aws_subnets = nc['subnets']
        task_execution.aws_ecs_security_groups = nc['securityGroups']
        task_execution.aws_ecs_assign_public_ip = \
                (nc['assignPublicIp'] == 'ENABLED')

        task_execution.save()
        task.latest_task_execution = task_execution
        task.save()

        try:
            ecs_client = run_env.make_boto3_client('ecs')

            overrides = {
                'containerOverrides': [
                    {
                        'name': task.aws_ecs_main_container_name,
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
                'executionRoleArn': execution_role_arn,
            }

            if task_role_arn:
                overrides['taskRoleArn'] = task_role_arn

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

            rv = ecs_client.run_task(**args)

            logger.info(f"Got run_task() return value {rv}")

            # TODO: handle failures in rv['failures'][]

            task_execution.aws_ecs_task_arn = rv['tasks'][0]['taskArn']
        except Exception:
            from ..models import TaskExecution
            logger.warning(f'Failed to start Task {task.uuid}', exc_info=True)
            task_execution.status = TaskExecution.Status.FAILED
            task_execution.stop_reason = TaskExecution.StopReason.FAILED_TO_START

            # TODO: add info from execption

            task_execution.finished_at = timezone.now()

        task_execution.save()

    def make_aws_ecs_service_name(self, index: int = 0) -> str:
        return 'CR_' + str(self.task.uuid) + '_' + str(index)

    def find_aws_ecs_service(self, ecs_client=None) -> Optional[Any]:
        task = self.task
        run_env = task.run_environment
        if ecs_client is None:
            ecs_client = run_env.make_boto3_client('ecs')

        service_arn_or_name = task.aws_ecs_service_arn or \
                self.make_aws_ecs_service_name()
        cluster = task.aws_ecs_default_cluster_arn or \
                run_env.aws_ecs_default_cluster_arn
        try:
            response_dict = ecs_client.describe_services(
                cluster=cluster,
                services=[service_arn_or_name])
            services = response_dict['services']

            if len(services) == 0:
                logger.info(f"No service named '{service_arn_or_name}' found for cluster '{cluster}'")
                return None

            return services[0]
        except Exception:
            logger.warning("Can't describe services", exc_info=True)
            return None

    def make_events_client(self):
        run_environment = self.task.run_environment
        return run_environment.make_boto3_client('events')

    def assign_public_ip_str(self, task_execution: Optional['TaskExecution'] = None) -> str:
        task = self.task
        run_env = task.run_environment

        assign_public_ip = False

        if task_execution and (task_execution.aws_ecs_assign_public_ip is not None):
            assign_public_ip = task_execution.aws_ecs_assign_public_ip
        elif task.aws_ecs_default_assign_public_ip is not None:
            assign_public_ip = task.aws_ecs_default_assign_public_ip
        elif run_env.aws_ecs_default_assign_public_ip is not None:
            assign_public_ip = run_env.aws_ecs_default_assign_public_ip

        if assign_public_ip:
            return 'ENABLED'

        return 'DISABLED'

    def make_common_args(self, include_launch_type: bool=True,
          task_execution: Optional['TaskExecution']=None) -> dict[str, Any]:
        from ..models.aws_ecs_configuration import AwsEcsConfiguration

        task = self.task
        run_env = task.run_environment
        cluster_arn = task.aws_ecs_default_cluster_arn \
                or run_env.aws_ecs_default_cluster_arn
        platform_version = task.aws_ecs_default_platform_version \
                or run_env.aws_ecs_default_platform_version \
                or AwsEcsConfiguration.PLATFORM_VERSION_LATEST
        task_definition_arn = task.aws_ecs_task_definition_arn

        subnets = task.aws_default_subnets or run_env.aws_default_subnets
        security_groups = task.aws_ecs_default_security_groups \
                or run_env.aws_ecs_default_security_groups
        assign_public_ip = self.assign_public_ip_str(
                task_execution=task_execution)

        if task_execution:
            cluster_arn =  task_execution.aws_ecs_cluster_arn or cluster_arn
            task_definition_arn = task_execution.aws_ecs_task_definition_arn \
                  or task_definition_arn
            subnets = task_execution.aws_subnets or subnets
            security_groups = task_execution.aws_ecs_security_groups \
                  or security_groups
            platform_version = task_execution.aws_ecs_platform_version \
                or platform_version

        args = dict(
            cluster=cluster_arn,
            taskDefinition=task_definition_arn,
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': subnets,
                    'securityGroups': security_groups,
                    'assignPublicIp': assign_public_ip
                }
            },
            platformVersion=platform_version,
        )

        if include_launch_type:
            # TODO: check that launch type is supported
            launch_type = task.aws_ecs_default_launch_type \
                    or run_env.aws_ecs_default_launch_type

            if task_execution:
                launch_type = task_execution.aws_ecs_launch_type or launch_type

            args['launchType'] = launch_type

        return args


    def make_common_service_args(self, include_launch_type: bool=True) \
            -> dict[str, Any]:

        task = self.task
        args = self.make_common_args(include_launch_type=include_launch_type)
        args['desiredCount'] =  task.service_instance_count

        deployment_configuration = {
            'maximumPercent': task.aws_ecs_service_deploy_maximum_percent or 200,
            'deploymentCircuitBreaker': {
                'enable': task.aws_ecs_service_deploy_enable_circuit_breaker or False,
                'rollback': task.aws_ecs_service_deploy_rollback_on_failure or False,
            }
        }

        p = 100
        if task.aws_ecs_service_deploy_minimum_healthy_percent is not None:
            p = task.aws_ecs_service_deploy_minimum_healthy_percent

        deployment_configuration['minimumHealthyPercent'] = p

        args['deploymentConfiguration'] = deployment_configuration

        return args

    def add_creation_args(self, args: dict[str, Any],
            task_execution: Optional['TaskExecution']=None) -> dict[str, Any]:
        task = self.task
        run_env = task.run_environment

        tags = (run_env.aws_tags or {}).copy()

        if task.aws_tags:
            tags.update(task.aws_tags)

        if task_execution:
            if task_execution.aws_tags:
                tags.update(task_execution.aws_tags)
        elif task.aws_ecs_service_tags:
            tags.update(task.aws_ecs_service_tags)

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

        managed = task.aws_ecs_enable_ecs_managed_tags \
            or run_env.aws_ecs_enable_ecs_managed_tags

        if managed is not None:
            args['enableECSManagedTags'] = managed

        return args
