from __future__ import annotations

from typing import Any, Optional, Mapping, NamedTuple, Tuple, TYPE_CHECKING, cast

from collections import abc
from datetime import datetime

import uuid

import pytest
from pytest_factoryboy import register

from django.conf import settings
from django.contrib.auth.models import User, Group

from rest_framework.authentication import BaseAuthentication
from rest_framework.request import (
    Request, ForcedAuthentication
)
from rest_framework.response import Response
from rest_framework.test import APIClient

from rest_framework_simplejwt.tokens import RefreshToken

from pytest_assert_utils import *

from processes.common.aws import extract_cluster_name
from processes.common.request_helpers import (
    context_with_request, make_fake_request
)
from processes.execution_methods import *
from processes.execution_methods.aws_settings import INFRASTRUCTURE_TYPE_AWS
from processes.execution_methods.aws_cloudwatch_scheduling_settings import SCHEDULING_TYPE_AWS_CLOUDWATCH
from processes.models import *
from processes.serializers import *

from tests.factories import (
    GroupFactory,
    GroupInfoFactory,
    UserFactory,
    SubscriptionPlanFactory,
    SubscriptionFactory,
    RunEnvironmentFactory,
    TaskFactory,
    UnknownTaskFactory,
    UnknownExecutionMethodTaskFactory,
    TaskExecutionFactory,
    WorkflowFactory,
    WorkflowTaskInstanceFactory,
    WorkflowTransitionFactory,
    WorkflowExecutionFactory,
    WorkflowTaskInstanceExecutionFactory,
    BasicEventFactory,
    TaskExecutionStatusChangeEventFactory,
    WorkflowExecutionStatusChangeEventFactory,
    MissingHeartbeatDetectionEventFactory,
    MissingScheduledTaskExecutionEventFactory,
    MissingScheduledWorkflowExecutionEventFactory,
    InsufficientServiceTaskExecutionsEventFactory,
    DelayedTaskExecutionStartEventFactory,
    NotificationProfileFactory,
    EmailNotificationDeliveryMethodFactory,
    PagerDutyNotificationDeliveryMethodFactory,
    NotificationFactory,    
)


SEND_ID_NONE = 'none'
SEND_ID_CORRECT = 'correct'
SEND_ID_WRONG = 'wrong'
SEND_ID_NOT_FOUND = 'not found'
SEND_ID_IN_WRONG_GROUP = 'in_wrong_group'
SEND_ID_WITH_OTHER_RUN_ENVIRONMENT = 'in_other_run_environment'
SEND_ID_WITHOUT_RUN_ENVIRONMENT = 'without_run_environment'
SEND_ID_OTHER = 'other'

SCOPE_TYPE_NONE = 'none'
SCOPE_TYPE_CORRECT = 'correct'
SCOPE_TYPE_OTHER = 'other'

CHANGE_ALL = '*'


register(GroupFactory)
register(GroupInfoFactory)
register(UserFactory)
register(SubscriptionPlanFactory)
register(SubscriptionFactory)
register(RunEnvironmentFactory)
register(TaskFactory)
register(UnknownTaskFactory)
register(UnknownExecutionMethodTaskFactory)
register(TaskExecutionFactory)
register(WorkflowFactory)
register(WorkflowTaskInstanceFactory)
register(WorkflowTransitionFactory)
register(WorkflowExecutionFactory)
register(WorkflowTaskInstanceExecutionFactory)

register(BasicEventFactory)
register(TaskExecutionStatusChangeEventFactory)
register(WorkflowExecutionStatusChangeEventFactory)
register(MissingHeartbeatDetectionEventFactory)
register(MissingScheduledTaskExecutionEventFactory)
register(MissingScheduledWorkflowExecutionEventFactory)
register(InsufficientServiceTaskExecutionsEventFactory)
register(DelayedTaskExecutionStartEventFactory)
register(NotificationProfileFactory)
register(EmailNotificationDeliveryMethodFactory)
register(PagerDutyNotificationDeliveryMethodFactory)
register(NotificationFactory)


@pytest.fixture(autouse=True)
def enable_db_debug_cursor():
    """
    Forces the Django database cursor to capture queries even if settings.DEBUG is False.
    """
    from django.db import connection

    if settings.LOG_SQL:
        connection.force_debug_cursor = True


@pytest.fixture
def api_client():
    return APIClient()

def make_saas_token_api_client(user: User, group: Group,
        api_client: APIClient, access_level: Optional[int] = None,
        run_environment: Optional[RunEnvironment] = None) -> APIClient:
    print(f"make_saas_token_api_client() {group=}, {run_environment=}, {access_level=}")

    token, _ = SaasToken.objects.get_or_create(user=user, group=group,
          access_level=access_level or UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
          run_environment=run_environment)
    api_client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
    return api_client

def make_jwt_token_api_client(user: User, api_client: APIClient) -> APIClient:
    header = cast(list[str], settings.SIMPLE_JWT['AUTH_HEADER_TYPES'])[0]
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'{header} {refresh.access_token}')
    return api_client

def make_api_client_from_options(api_client: APIClient,
        is_authenticated: bool = False,
        user: Optional[User] = None, group: Optional[Group] = None,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> APIClient:
    if not is_authenticated:
        return api_client

    if user is None:
        raise RuntimeError('No user')

    if api_key_access_level is None:
        assert(api_key_run_environment is None)
        return make_jwt_token_api_client(user=user, api_client=api_client)

    if group is None:
        raise RuntimeError('No group')

    return make_saas_token_api_client(user=user, group=group,
            api_client=api_client, access_level=api_key_access_level,
            run_environment=api_key_run_environment)

def set_group_access_level(user: User, group: Group,
        access_level: Optional[int]) -> None:
    if access_level is None:
        UserGroupAccessLevel.objects.filter(user=user, group=group).delete()
        user.groups.remove(group)
    else:
        ugal, _created = UserGroupAccessLevel.objects.get_or_create(
                user=user, group=group, defaults={'access_level': access_level})
        ugal.access_level = access_level
        ugal.save()
        user.groups.add(group)

def authenticated_request_for_context(user: User,
        group: Optional[Group],
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None,
        path: Optional[str] = None,  **kwargs) -> Request:
    if api_key_access_level is None:
        assert api_key_run_environment is None
        auth = RefreshToken.for_user(user)
    else:
        assert group is not None
        auth = SaasToken(user=user, group=group,
                run_environment=api_key_run_environment,
                access_level=api_key_access_level)

    authenticators = [cast(BaseAuthentication,
          ForcedAuthentication(user, auth)),]

    print(f"Making fake request with auth {type(auth).__name__}")
    return make_fake_request(authenticators=authenticators, **kwargs)

def context_with_authenticated_request(**kwargs) -> dict[str, Any]:
    return {
        'request': authenticated_request_for_context(**kwargs)
    }

def check_validation_error(response: Response,
        validation_error_attribute: Optional[str] = None,
        error_code: Optional[str] = None) -> None:
    if validation_error_attribute:
        response_dict = cast(dict[str, Any], response.data)
        assert(validation_error_attribute in response_dict)

        if error_code:
            assert(response_dict[validation_error_attribute][0].code == error_code)

def iso8601_with_z(dt: Optional[datetime]) -> Optional[str]:
    if dt:
        return dt.isoformat().replace('+00:00', 'Z')

    return None

def split_url(url: str) -> Tuple[Optional[str], str]:
    double_slash_index = url.find('//')
    if double_slash_index >= 0:
        next_slash_index = url.find('/', double_slash_index + 2)

        if next_slash_index >= 0:
            return (url[0:next_slash_index], url[next_slash_index:])

        return (url, '')

    return (None, url)

def verify_name_uuid_url_match(body_1: dict[str, Any],
        body_2: dict[str, Any], check_name: bool = True) -> None:
    assert(body_1['uuid'] == body_2['uuid'])

    if check_name:
        assert(body_1['name'] == body_2['name'])

    url_1 = body_1.get('url')
    url_2 = body_2.get('url')

    if url_1 is None:
        assert url_2 is None
    else:
        assert url_2 is not None

        t_1 = split_url(url_1)
        t_2 = split_url(url_2)

        if (t_1[0] is not None) and (t_2[0] is not None):
            assert t_1[0] == t_2[0]

        assert t_1[1] == t_2[1]


def assert_deep_subset(subset: Any, superset: Any, attr: Optional[str]=None) \
        -> None:
    attr = attr or '(unknown)'

    if isinstance(subset, str): # Because string is iterable
        assert subset == superset, f"{attr=}, {subset=} not a subset of {superset=}"
    elif isinstance(subset, abc.Mapping):
        assert isinstance(superset, abc.Mapping)
        for k, v in subset.items():
            assert k in superset
            assert_deep_subset(v, superset[k], f"{attr}.{k}")
    elif isinstance(subset, abc.Sequence):
        assert isinstance(superset, abc.Sequence)
        assert len(subset) == len(superset)

        for i, v in enumerate(subset):
            assert_deep_subset(v, superset[i], f"{attr}[{i}]")
    else:
        assert subset == superset, f"{attr=}, {subset=} != {superset=}"


def ensure_attributes_match(body_dict: dict[str, Any], model,
        attrs: list[str], partial: bool=False) -> None:
    for attr in attrs:
        if partial and (attr not in body_dict):
            continue

        expected = getattr(model, attr)

        if attr.find('uuid') >= 0:
            expected = str(expected)
        elif isinstance(expected, datetime):
            expected = expected.isoformat().replace('+00:00', 'Z')

        actual = body_dict[attr]

        assert actual == expected, f"{attr=}, {actual=}, {expected=}"

COPIED_AWS_NETWORK_ATTRIBUTES = [
    'region',
    'availability_zone',
    'subnets',
    'security_groups',
    'assign_public_ip',
]

COPIED_RUN_ENVIRONMENT_ATTRIBUTES = [
    'name', 'description',
]

OUTPUT_RUN_ENVIRONMENT_ATTRIBUTES = COPIED_RUN_ENVIRONMENT_ATTRIBUTES

EXECUTABLE_ATTRIBUTES = [
    'enabled',
    'schedule', 'scheduled_instance_count',
    'max_concurrency',
    'max_age_seconds', 'default_max_retries',
    'postponed_failure_before_success_seconds',
    'max_postponed_failure_count',
    'max_postponed_timeout_count',
    'min_missing_execution_delay_seconds',
    'postponed_missing_execution_before_start_seconds',
    'max_postponed_missing_execution_count',
    'min_missing_execution_delay_seconds',
    'required_success_count_to_clear_failure',
    'required_success_count_to_clear_timeout',
]

COPIED_TASK_ATTRIBUTES = [
    'name', 'description', 'project_url', 'log_query',
    'enabled', 'was_auto_created', 'passive',
    'max_manual_start_delay_before_alert_seconds',
    'max_manual_start_delay_before_abandonment_seconds',
    'heartbeat_interval_seconds',
    'max_heartbeat_lateness_before_alert_seconds',
    'max_heartbeat_lateness_before_abandonment_seconds',
    'is_service', 'service_instance_count', 'min_service_instance_count',
    'schedule', 'scheduled_instance_count', 'max_concurrency',
    'execution_method_type',
    'default_input_value', 'input_value_schema', 'output_value_schema',
    'managed_probability', 'failure_report_probability',
    'timeout_report_probability',
] + EXECUTABLE_ATTRIBUTES

ENHANCED_TASK_ATTRIBUTES = [
   'execution_method_capability_details',
   'infrastructure_settings',
   'scheduling_settings',
   'service_settings',
]

OUTPUT_TASK_ATTRIBUTES = COPIED_TASK_ATTRIBUTES + ENHANCED_TASK_ATTRIBUTES + [
   'uuid', 'dashboard_url', 'logs_url',
   'created_at', 'updated_at',
]

COPIED_TASK_EXECUTION_ATTRIBUTES = [
    'task_version_number', 'task_version_signature', 'task_version_text',
    'heartbeat_interval_seconds', 'hostname',
    'other_instance_metadata',
    'failed_attempts', 'timed_out_attempts', 'exit_code',
    'last_status_message', 'success_count', 'error_count', 'skipped_count',
    'expected_count', 'other_runtime_metadata',
    'current_cpu_units', 'mean_cpu_units', 'max_cpu_units',
    'current_memory_mb', 'mean_memory_mb', 'max_memory_mb',
    'wrapper_version', 'wrapper_log_level', 'deployment',
    'process_command', 'is_service', 'task_max_concurrency',
    'max_conflicting_age_seconds', 'prevent_offline_execution',
    'process_timeout_seconds',
    'process_termination_grace_period_seconds',
    'process_max_retries', 'process_max_retries', 'process_retry_delay_seconds',
    'schedule',
    'heartbeat_interval_seconds',
    'api_request_timeout_seconds',
    'api_retry_delay_seconds',
    'api_resume_delay_seconds',
    'api_error_timeout_seconds',
    'api_task_execution_creation_error_timeout_seconds',
    'api_task_execution_creation_conflict_timeout_seconds',
    'api_task_execution_creation_conflict_retry_delay_seconds',
    'api_final_update_timeout_seconds',
    'status_update_interval_seconds',
    'status_update_port', 'status_update_message_max_bytes',
    'debug_log_tail', 'error_log_tail',
    'embedded_mode',
    'auto_created_task_properties',
    'input_value', 'output_value', 'error_details',
]

ENHANCED_TASK_EXECUTION_ATTRIBUTES = [
   'execution_method_details',
   'infrastructure_settings',
]

OUTPUT_TASK_EXECUTION_ATTRIBUTES = COPIED_TASK_EXECUTION_ATTRIBUTES \
    + ENHANCED_TASK_EXECUTION_ATTRIBUTES + [
   'uuid', 'dashboard_url', 'created_at', 'updated_at',
]


def make_common_task_request_body(run_environment_name: str = 'Staging',
        was_auto_created: bool = False) -> dict[str, Any]:
    return {
        'name': 'A Task',
        'description': 'Does something',
        'project_url': 'https://github.com/ExampleOrg/hello',
        'max_age_seconds': 1800,
        'heartbeat_interval_seconds': 600,
        'was_auto_created': was_auto_created,
        'run_environment': {
          'name': run_environment_name
        },
        'log_query': '/aws/fargate/hello_world-' + run_environment_name,
        'links': [
            {
                'name': 'Rollbar',
                'link_url_template': 'https://www.rollbar.com/MyCorp/hello'
            }
        ]
    }


def validate_serialized_run_environment(body_re: dict[str, Any], model_re: run_environment,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_re, model_re, OUTPUT_RUN_ENVIRONMENT_ATTRIBUTES)

    assert body_re['created_by_group'] == GroupSerializer(
            model_re.created_by_group,
            include_users=False, context=context).data

    assert model_re.created_by_user is not None # for mypy

    assert body_re['created_by_user'] == model_re.created_by_user.username

    if model_re.aws_settings:
        expected_aws_settings = model_re.aws_settings.copy()
        del expected_aws_settings['secret_key']

        assert body_re['infrastructure_settings'][INFRASTRUCTURE_TYPE_AWS][
            RunEnvironmentSerializer.DEFAULT_LABEL][RunEnvironmentSerializer.SETTINGS_KEY] == expected_aws_settings

    if model_re.default_aws_ecs_configuration:
        assert body_re['execution_method_settings'][AwsEcsExecutionMethod.NAME][
            RunEnvironmentSerializer.DEFAULT_LABEL][RunEnvironmentSerializer.SETTINGS_KEY] == model_re.default_aws_ecs_configuration


def validate_saved_run_environment(body_re: dict[str, Any],
        model_re: RunEnvironment,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_re, model_re, COPIED_RUN_ENVIRONMENT_ATTRIBUTES,
            partial=True)

    assert body_re['created_by_group'] == GroupSerializer(
            model_re.created_by_group,
            include_users=False, context=context).data

    assert model_re.created_by_user is not None # for mypy

    assert body_re['created_by_user'] == model_re.created_by_user.username

    infra_settings = body_re.get('infrastructure_settings')
    if infra_settings:
        name_to_aws_settings_container = infra_settings.get(INFRASTRUCTURE_TYPE_AWS)
        if name_to_aws_settings_container:
            for name, aws_settings_container in name_to_aws_settings_container.items():
                if name == RunEnvironmentSerializer.DEFAULT_LABEL:
                    aws_settings = aws_settings_container.get(RunEnvironmentSerializer.SETTINGS_KEY)
                    if aws_settings is None:
                        assert_deep_subset(aws_settings, model_re.aws_settings)

    em_defaults = body_re.get('execution_method_settings')

    if em_defaults is not None:
        for emt, em_settings in em_defaults.items():
            for execution_method_name, meta_settings in em_settings.items():
                if execution_method_name == RunEnvironmentSerializer.DEFAULT_LABEL:
                    meta_settings = meta_settings or {}
                    em_settings = meta_settings.get(RunEnvironmentSerializer.SETTINGS_KEY)

                    if emt == AwsEcsExecutionMethod.NAME:
                        assert_deep_subset(em_settings, model_re.default_aws_ecs_configuration)


class AwsEcsSetup(NamedTuple):
    cluster: Mapping[str, Any]
    task_definition: Mapping[str, Any]
    subnets: list[str]
    security_groups: list[str]

    @property
    def task_definition_arn(self) -> str:
        return cast(str, self.task_definition['taskDefinitionArn'])

def setup_aws_ecs_cluster(run_environment: RunEnvironment) -> str:
    ecs_client = run_environment.make_boto3_client('ecs')
    cluster_response = ecs_client.create_cluster(
            clusterName=extract_cluster_name(run_environment.aws_ecs_default_cluster_arn))
    return cluster_response['cluster']

def setup_aws_ecs(run_environment: RunEnvironment) -> AwsEcsSetup:
    ec2_client = run_environment.make_boto3_client('ec2')

    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")

    vpc_id = vpc["Vpc"]["VpcId"]

    subnet1 = ec2_client.create_subnet(
        AvailabilityZone="us-west-2a",
        CidrBlock="10.0.0.0/24",
        VpcId=vpc_id,
    )

    subnet2 = ec2_client.create_subnet(
        AvailabilityZone="us-west-2a",
        CidrBlock="10.0.1.0/24",
        VpcId=vpc_id,
    )

    sg1 = ec2_client.create_security_group(
        Description="Security Group 1",
        GroupName="sg1",
        VpcId=vpc_id,
    )

    sg2 = ec2_client.create_security_group(
        Description="Security Group 2",
        GroupName="sg2",
        VpcId=vpc_id,
    )

    ecs_client = run_environment.make_boto3_client('ecs')
    cluster_response = ecs_client.create_cluster(
            clusterName=extract_cluster_name(run_environment.aws_ecs_default_cluster_arn))
    print(f"{cluster_response=}")

    task_def_response = ecs_client.register_task_definition(family='nginx',
        executionRoleArn=run_environment.aws_ecs_default_execution_role,
        networkMode='awsvpc',
        containerDefinitions=[{
            "name": "nginx",
            "image": "nginx:latest",
            "memory": 256,
            "cpu": 256,
            "essential": True,
            "portMappings": [
              {
                "containerPort": 80,
                "protocol": "tcp"
              }
            ],
            "logConfiguration":{
                 "logDriver":"awslogs",
                  "options": {
                      "awslogs-group": "awslogs-nginx-ecs",
                      "awslogs-region": "us-east-1",
                      "awslogs-stream-prefix":"ecs"
                  }
            }
        }])

    print(f"{task_def_response=}")

    return AwsEcsSetup(cluster=cluster_response['cluster'],
        task_definition=task_def_response['taskDefinition'],
        subnets=[subnet1['Subnet']['SubnetId'], subnet2['Subnet']['SubnetId']],
        security_groups=[sg1['GroupId'], sg2['GroupId']])


def make_aws_ecs_task_request_body(run_environment: RunEnvironment,
        aws_ecs_setup: AwsEcsSetup,
        is_service: bool = False, schedule: str = '',
        was_auto_created: bool = False,
        is_legacy_schema=False) -> dict[str, Any]:
    body = make_common_task_request_body(
            run_environment_name=run_environment.name,
            was_auto_created=was_auto_created)

    body['schedule'] = schedule

    if is_service:
        body['service_instance_count'] = 1

    task_definition_arn = aws_ecs_setup.task_definition_arn

    if is_legacy_schema:
        emc = {
            'type': 'AWS ECS',
            'task_definition_arn': task_definition_arn,
            'default_launch_type': 'FARGATE',
            'supported_launch_types': ['FARGATE'],
            'default_platform_version': '1.4.0',
            'main_container_name': 'hello',
            'allocated_cpu_units': 1024,
            'allocated_memory_mb': 2048,
            'default_execution_role': run_environment.aws_ecs_default_execution_role,
            'default_task_role': 'arn:aws:iam::123456789012:role/task',
            'default_subnets': aws_ecs_setup.subnets,
            'default_security_groups': aws_ecs_setup.security_groups,
            'tags': {
                'TagA': 'A',
                'TagB': 'B'
            },
        }

        if is_service:
            emc['service_options'] = {
                'load_balancers': [
                    {
                        'target_group_arn': 'arn:aws:elasticloadbalancing:us-west-1:123456789012:targetgroup/example-web/hello',
                        'container_name': 'hello',
                        'container_port': 8080
                    }
                ],
                'load_balancer_health_check_grace_period_seconds': 60,
                'force_new_deployment': True,
                'deploy_minimum_healthy_percent': 50,
                'deploy_maximum_percent': 200,
                'deploy_enable_circuit_breaker': True,
                'deploy_rollback_on_failure': False,
                'enable_ecs_managed_tags': True,
                'propagate_tags': 'SERVICE',
                'tags': {
                    'TagC': 'C',
                    'TagD': 'D'
                }
            }

        body['execution_method_capability'] = emc
    else:
        body['allocated_cpu_units'] = 1024
        body['allocated_memory_mb'] = 2048
        body['execution_method_type'] = 'AWS ECS'
        body['execution_method_capability_details'] = {
            'task_definition_arn': task_definition_arn,
            'launch_type': 'FARGATE',
            'supported_launch_types': ['FARGATE'],
            'platform_version': '1.4.0',
            'main_container_name': 'hello',
            'execution_role_arn': run_environment.aws_ecs_default_execution_role,
            'task_role_arn': 'arn:aws:iam::123456789012:role/task'
        }
        body['infrastructure_type'] = 'AWS'
        body['infrastructure_settings'] = {
            'region': 'us-west-1',
            'network': {
                'subnets': aws_ecs_setup.subnets,
                'security_groups': aws_ecs_setup.security_groups,
            },
            'logging': {
                'driver': 'awslogs',
                'options': {
                    'group': '/aws/fargate/hello_world-' + run_environment.name,
                    'region': 'us-west-1',
                    'stream_prefix': 'hello_world-' + run_environment.name
                }
            },
            'tags': {
                'TagA': 'A',
                'TagB': 'B'
            }
        }

        if is_service:
            body['service_provider_type'] = SERVICE_PROVIDER_AWS_ECS
            body['service_settings'] = {
                'deployment_configuration': {
                    'minimum_healthy_percent': 50,
                    'maximum_percent': 200,
                    'deployment_circuit_breaker': {
                        'enable': True,
                        'rollback_on_failure': False
                    }
                },
                'force_new_deployment': True,
                'load_balancer_settings': {
                    'load_balancers': [
                        {
                            'target_group_arn': 'arn:aws:elasticloadbalancing:us-west-1:123456789012:targetgroup/example-web/hello',
                            'container_name': 'hello',
                            'container_port': 8080
                        }
                    ],
                    'health_check_grace_period_seconds': 60,
                },
                'enable_ecs_managed_tags': True,
                'propagate_tags': 'SERVICE',
                'tags': {
                    'TagC': 'C',
                    'TagD': 'D'
                }
            }

        if schedule:
            body['scheduling_provider_type'] = SCHEDULING_TYPE_AWS_CLOUDWATCH

    return body


def make_unknown_task_request_body(run_environment: RunEnvironment) -> dict[str, Any]:
    body = make_common_task_request_body(
            run_environment_name=run_environment.name,
            was_auto_created=True)

    body['execution_method_type'] = UnknownExecutionMethod.NAME

    # Not necessary since TaskSerializer infers this from the Unknown
    # execution method type.
    # body['passive'] = True

    return body


def validate_serialized_task(body_task: dict[str, Any], model_task: Task,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_task, model_task, OUTPUT_TASK_ATTRIBUTES)

    assert body_task['created_by_group'] == GroupSerializer(
            model_task.created_by_group,
            include_users=False, context=context).data

    assert model_task.created_by_user is not None # for mypy

    assert body_task['created_by_user'] == model_task.created_by_user.username

    run_environment_dict = NameAndUuidSerializer(
            model_task.run_environment, context=context,
            view_name='run_environments-detail').data

    verify_name_uuid_url_match(body_task['run_environment'],
            run_environment_dict)

    model_links = TaskLink.objects.filter(task__id=model_task.id).all()
    body_links = body_task['links']

    assert len(model_links) == len(body_links)

    for model_link in model_links:
        body_link = [link for link in body_links
                if link['link_url_template'] == model_link.link_url_template][0]
        assert body_link is not None
        ensure_attributes_match(body_link, model_link,
            ['description', 'icon_url', 'rank'])

    if model_task.latest_task_execution is None:
        assert body_task['latest_task_execution'] is None


def validate_saved_task(body_task: dict[str, Any], model_task: Task,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_task, model_task, COPIED_TASK_ATTRIBUTES,
            partial=True)

    if 'run_environment' in body_task:
        body_run_environment = body_task['run_environment']
        if 'uuid' in body_run_environment:
            assert model_task.run_environment.uuid == body_run_environment['uuid']

        if 'name' in body_run_environment:
            assert model_task.run_environment.name == body_run_environment['name']

    for attr in ENHANCED_TASK_ATTRIBUTES:
        if attr in body_task:
            assert_deep_subset(body_task[attr], getattr(model_task, attr), attr)

    execution_method_type = ''
    service_provider_type = ''

    # Deprecated schema
    emc = body_task.get('execution_method_capability')
    if emc is not None:
        execution_method_type = emc['type']
        for attr in ['allocated_cpu_units', 'allocated_memory_mb']:
            if attr in emc:
                assert getattr(model_task, attr) == emc[attr]

        model_infra = AwsSettings.parse_obj(model_task.infrastructure_settings)
        model_network = model_infra.network

        if 'default_subnets' in emc:
            assert model_network is not None
            assert model_network.subnet_infrastructure_website_urls is not None
            assert len(model_network.subnet_infrastructure_website_urls) == len(emc['default_subnets'])
            for i, subnet in enumerate(emc['default_subnets']):
                assert model_network.subnet_infrastructure_website_urls[i].index(subnet) >= 0

        if 'default_security_groups' in emc:
            assert model_network is not None
            assert model_network.security_group_infrastructure_website_urls is not None
            assert len(model_network.security_group_infrastructure_website_urls) == len(emc['default_security_groups'])
            for i, security_group in enumerate(emc['default_security_groups']):
                assert model_network.security_group_infrastructure_website_urls[i].index(security_group) >= 0

        service_options = emc.get('service_options')

        nullable_service_attrs = [
            'load_balancer_health_check_grace_period_seconds',
            'deploy_enable_circuit_breaker',
            'deploy_rollback_on_failure',
            'deploy_minimum_healthy_percent',
            'deploy_maximum_percent',
            'enable_ecs_managed_tags',
            'tags'
        ]

        if service_options is None:
            assert model_task.service_instance_count is None
            assert model_task.service_provider_type == ''
            assert model_task.service_settings is None
        else:
            service_provider_type = SERVICE_PROVIDER_AWS_ECS

            assert model_task.service_instance_count is not None
            assert model_task.service_instance_count >= 1

            assert model_task.service_provider_type == 'AWS ECS'
            assert model_task.service_settings is not None

    execution_method_type = body_task.get('execution_method_type') or \
            execution_method_type

    emcd = body_task.get('execution_method_capability_details')

    infra = body_task.get('infrastructure_settings')

    if infra is not None:
        if body_task.get('infrastructure_type') == INFRASTRUCTURE_TYPE_AWS:
            model_infra = AwsSettings.parse_obj(model_task.infrastructure_settings)

            ensure_attributes_match(infra, model_infra,
                    ['tags'], partial=True)

            aws_network = infra.get('network')
            if aws_network is not None:
                model_network = model_infra.network
                ensure_attributes_match(aws_network, model_network,
                        COPIED_AWS_NETWORK_ATTRIBUTES, partial=True)

                if 'subnets' in aws_network:
                    assert model_network is not None
                    assert model_network.subnet_infrastructure_website_urls is not None
                    assert len(model_network.subnet_infrastructure_website_urls) == len(aws_network['subnets'])
                    for i, subnet in enumerate(aws_network['subnets']):
                        assert model_network.subnet_infrastructure_website_urls[i].index(subnet) >= 0

                if 'security_groups' in aws_network:
                    assert model_network is not None
                    assert model_network.security_group_infrastructure_website_urls is not None
                    assert len(model_network.security_group_infrastructure_website_urls) == len(aws_network['security_groups'])
                    for i, subnet in enumerate(aws_network['security_groups']):
                        assert model_network.security_group_infrastructure_website_urls[i].index(subnet) >= 0

            aws_logging = infra.get('logging')
            if aws_logging is not None:
                model_logging = model_infra.logging
                assert model_logging is not None
                ensure_attributes_match(aws_network, model_logging,
                        ['driver'], partial=True)

                log_options = aws_logging.get('options')
                if log_options is not None:
                    ensure_attributes_match(log_options, model_logging.options,
                        ['group', 'region', 'stream_prefix'], partial=True)

                if (aws_logging.get('driver') == 'awslogs') and ('group' in aws_logging):
                    assert model_logging.infrastructure_website_url is not None

    service_provider_type = body_task.get('service_provider_type') or \
            service_provider_type
    body_service_settings = body_task.get('service_settings')

    if service_provider_type:
        assert model_task.service_provider_type == service_provider_type
        model_service_settings = model_task.service_settings
        assert model_service_settings is not None
    else:
        assert body_service_settings is None
        assert model_task.service_provider_type == ''
        assert model_task.service_settings is None

    if body_task.get('schedule'):
        body_is_scheduling_managed = body_task.get('is_scheduling_managed')
        if body_is_scheduling_managed is None:
            assert model_task.is_scheduling_managed
        else:
            assert model_task.is_scheduling_managed == body_is_scheduling_managed

        if execution_method_type == AwsEcsExecutionMethod.NAME:
            assert model_task.scheduling_provider_type == SCHEDULING_TYPE_AWS_CLOUDWATCH
        else:
            assert model_task.scheduling_provider_type == body_task.get('scheduling_provider_type') or ''
        assert model_task.scheduling_settings is not None
    else:
        assert model_task.scheduling_provider_type == ''
        assert model_task.scheduling_settings is None

    if model_task.is_service:
        body_is_service_managed = body_task.get('is_service_managed')
        if body_is_service_managed is None:
            assert model_task.is_service_managed
        else:
            assert model_task.is_service_managed == body_is_service_managed


def make_task_execution_request_body(uuid_send_type: Optional[str],
        task_send_type: Optional[str],
        user: User,
        group_factory, run_environment_factory, task_factory,
        task_execution_factory,
        task_execution_status: str = 'RUNNING',
        task_property_name: str = 'task',
        api_key_run_environment: Optional[RunEnvironment] = None,
        task_execution: Optional[TaskExecution] = None,
        task: Optional[Task] = None) -> dict[str, Any]:
    request_data: dict[str, Any] = {
      'status': task_execution_status,
      'extraprop': 'dummy',
    }

    run_environment: Optional[RunEnvironment] = None

    if task_send_type == SEND_ID_CORRECT:
        if (task is None) and task_execution:
            task = task_execution.task
    elif task_send_type == SEND_ID_WITH_OTHER_RUN_ENVIRONMENT:
        run_environment = run_environment_factory(created_by_group=user.groups.first())
    elif task_send_type == SEND_ID_IN_WRONG_GROUP:
        group = group_factory()
        set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
        run_environment = run_environment_factory(created_by_group=group)

    # TODO set created by group from run_environment
    if task is None:
        if run_environment is None:
            if api_key_run_environment:
                run_environment = api_key_run_environment
            elif task_execution:
                run_environment = task_execution.task.run_environment
            else:
                run_environment = run_environment_factory(created_by_group=user.groups.first())

        assert run_environment is not None
        task = task_factory(
            created_by_group=run_environment.created_by_group,
            run_environment=run_environment)

    if task_send_type:
        if task_send_type == SEND_ID_NONE:
            request_data[task_property_name] = None
        else:
            assert task is not None  # for mypy
            request_data[task_property_name] = {
                'uuid': str(task.uuid)
            }

    if uuid_send_type == SEND_ID_NOT_FOUND:
        request_data['uuid'] = str(uuid.uuid4())
    elif uuid_send_type == SEND_ID_CORRECT:
        assert task_execution is not None
        request_data['uuid'] = str(task_execution.uuid)
    elif uuid_send_type == SEND_ID_WRONG:
        assert task is not None
        another_task_execution = task_execution_factory(
                task=task)
        request_data['uuid'] = str(another_task_execution.uuid)

    return request_data


def make_aws_ecs_task_execution_request_body(
        run_environment: Optional[RunEnvironment],
        group_factory, run_environment_factory, task_factory,
        task_execution_factory,
        user: User,
        uuid_send_type: Optional[str] = SEND_ID_NONE,
        task_send_type: Optional[str] = SEND_ID_CORRECT,
        task_execution: Optional[TaskExecution] = None,
        task_execution_status: str = 'RUNNING',
        task_property_name: str = 'task',
        task: Optional[Task] = None,
        aws_ecs_setup: Optional[AwsEcsSetup] = None,
        was_auto_created: bool = False, is_passive: bool = False,
        is_legacy_schema: bool = False) -> dict[str, Any]:
    body = make_task_execution_request_body(
        uuid_send_type = uuid_send_type,
        task_send_type = task_send_type,
        user = user,
        api_key_run_environment = run_environment,
        task_execution = task_execution,
        group_factory = group_factory,
        run_environment_factory = run_environment_factory,
        task_factory = task_factory,
        task_execution_factory = task_execution_factory,
        task_execution_status = task_execution_status,
        task_property_name = task_property_name,
        task = task
    )

    task_request_fragment: dict[str, Any] = {}

    if task_send_type == SEND_ID_CORRECT:
        if task:
            task_request_fragment = {
                'name': task.name
            }
        else:
            assert run_environment is not None
            task_request_fragment = make_aws_ecs_task_request_body(
                run_environment=run_environment,
                aws_ecs_setup=aws_ecs_setup,
                was_auto_created=was_auto_created,
                is_legacy_schema=is_legacy_schema)

        task_request_fragment["passive"] = is_passive

        body['task'] = task_request_fragment

    default_attr_prefix = ''
    if is_legacy_schema:
        emcd = task_request_fragment.get('execution_method_capability')
        default_attr_prefix = 'default_'
    else:
        emcd = task_request_fragment.get('execution_method_capability_details')

    emcd = emcd or {}

    launch_type = emcd.get(default_attr_prefix + "launch_type", "FARGATE")
    emd = {
        "task_arn": "arn:aws:ecs:us-east-1:012345678910:task/9781c248-0edd-4cdb-9a93-f63cb662a5d3",
        "task_definition_arn": emcd.get('task_definition_arn', aws_ecs_setup.task_definition_arn),
        "launch_type": launch_type
    }

    cluster_arn = emcd.get(default_attr_prefix + "cluster_arn")

    if not cluster_arn:
        assert run_environment is not None
        cluster_arn = run_environment.aws_ecs_default_cluster_arn

    emd["cluster_arn"] = cluster_arn

    if is_legacy_schema:
        emd["type"] = "AWS ECS"
        body['execution_method'] = emd
    else:
        body['execution_method_type'] = AwsEcsExecutionMethod.NAME
        body['execution_method_details'] = emd

        infra_type = task_request_fragment.get('infrastructure_type')
        if infra_type:
            body['infrastructure_type'] = infra_type

            infra = task_request_fragment.get('infrastructure_settings') or {}

            te_logging = (infra.get('logging') or {}).copy()
            te_logging.pop('stream_prefix', None)
            te_logging['stream'] = "ecs/curl/cd189a933e5849daa93386466019ab50"

            body['infrastructure_settings'] = {
                'region': 'us-east-2',
                'network': {
                    "region": "us-east-2",
                    "availability_zone": "us-east-2a",
                    "networks": [
                        {
                            "network_mode": "awsvpc",
                            "ip_v4_subnet_cidr_block": "192.0.2.0/24",
                            "dns_servers": ["192.0.2.2"],
                            "dns_search_list": ["us-west-2.compute.internal"],
                            "private_dns_name": "ip-10-0-0-222.us-east-2.compute.internal",
                            "subnet_gateway_ip_v4_address": "192.0.2.0/24"
                        }
                    ]
                },
                'logging': te_logging
            }

    return body

def validate_serialized_task_execution(body_task_execution: dict[str, Any],
        model_task_execution: TaskExecution,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_task_execution, model_task_execution,
        OUTPUT_TASK_EXECUTION_ATTRIBUTES)

    task_dict = NameAndUuidSerializer(
            model_task_execution.task, context=context,
            view_name='tasks-detail').data

    verify_name_uuid_url_match(body_task_execution['task'],
            task_dict)

    assert body_task_execution['status'] == TaskExecution.Status(
            model_task_execution.status).name

    if model_task_execution.started_by:
        assert body_task_execution['started_by'] == model_task_execution \
                .started_by.username
    else:
        assert body_task_execution['started_by'] is None

    if model_task_execution.stop_reason is None:
        assert body_task_execution['stop_reason'] is None
    else:
        body_task_execution['stop_reason'] == TaskExecution.StopReason(
            model_task_execution.stop_reason).name

    if model_task_execution.marked_done_by is None:
        assert body_task_execution['marked_done_by'] is None
    else:
        body_task_execution['marked_done_by'] == model_task_execution \
                .marked_done_by.username

    if model_task_execution.killed_by is None:
        assert body_task_execution['killed_by'] is None
    else:
        body_task_execution['killed_by'] == model_task_execution \
                .killed_by.username

    try:
        wtie = model_task_execution.workflowtaskinstanceexecution
        wtie_dict = NameAndUuidSerializer(wtie, include_name=False,
                context=context).data
        verify_name_uuid_url_match(
                body_task_execution['workflow_task_instance_execution'],
                wtie_dict, check_name=False)
    except WorkflowTaskInstanceExecution.DoesNotExist:
        assert body_task_execution['workflow_task_instance_execution'] is None


def validate_saved_task_execution(body_task_execution: dict[str, Any],
        model_task_execution: TaskExecution,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_task_execution, model_task_execution,
            COPIED_TASK_EXECUTION_ATTRIBUTES, partial=True)

    for attr in ENHANCED_TASK_EXECUTION_ATTRIBUTES:
        if attr in body_task_execution:
            print(f"body task execution[{attr}] = {body_task_execution[attr]}")
            print(f"model[{attr}] = {getattr(model_task_execution, attr)}")
            assert_deep_subset(body_task_execution[attr],
                    getattr(model_task_execution, attr), attr)

    body_task = body_task_execution.get('task')
    model_task = model_task_execution.task

    if body_task and (body_task.get('was_auto_created') == True):
        assert 'uuid' not in body_task_execution
        assert isinstance(body_task, dict)
        assert 'uuid' not in body_task
        assert 'name' in body_task
        validate_saved_task(body_task=body_task,
                model_task=model_task,
                context=context)
        assert model_task.was_auto_created
    else:
        assert not model_task.was_auto_created
        if body_task:
            if 'uuid' in body_task:
                assert body_task['uuid'] == str(model_task.uuid)
            elif 'name' in body_task:
                assert body_task['name'] == str(model_task.name)
            else:
                assert False, "uuid or name must be present in task object"
        else:
            assert 'uuid' in body_task_execution
            assert body_task_execution['uuid'] == str(model_task_execution.uuid)
            assert body_task_execution['status'] != 'MANUALLY_STARTED'


def validate_serialized_workflow(body_workflow: dict[str, Any],
        model_workflow: Workflow,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_workflow, model_workflow, [
        'uuid', 'name', 'description', 'dashboard_url',
        'schedule', 'max_concurrency',
        'max_age_seconds', 'default_max_retries',
        'latest_workflow_execution',
        'enabled',
        'created_at', 'updated_at'
    ] + EXECUTABLE_ATTRIBUTES)

    assert body_workflow['created_by_group'] == GroupSerializer(
            model_workflow.created_by_group,
            include_users=False, context=context).data

    assert model_workflow.created_by_user is not None # for mypy

    assert body_workflow['created_by_user'] == model_workflow.created_by_user.username

    run_environment_dict = NameAndUuidSerializer(
            model_workflow.run_environment, context=context,
            view_name='run_environments-detail').data

    verify_name_uuid_url_match(body_workflow['run_environment'],
            run_environment_dict)

    if model_workflow.latest_workflow_execution is None:
        assert body_workflow['latest_workflow_execution'] is None
    else:
        validate_serialized_workflow_execution_summary(
                body_workflow['latest_workflow_execution'],
                model_workflow.latest_workflow_execution,
                context=context)


def validate_serialized_workflow_execution_summary(
        body_workflow_execution: dict[str, Any],
        model_workflow_execution: WorkflowExecution,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_workflow_execution, model_workflow_execution, [
        'uuid', 'dashboard_url',
        'started_at', 'finished_at', 'last_heartbeat_at',
        'stop_reason', 'marked_done_at',
        'kill_started_at', 'kill_finished_at',
        'kill_error_code',
        'failed_attempts', 'timed_out_attempts',
        'created_at', 'updated_at'
    ])

    assert body_workflow_execution['status'] == Execution.Status(
            model_workflow_execution.status).name

    if body_workflow_execution['run_reason'] is None:
        assert model_workflow_execution.run_reason == WorkflowExecution.RunReason.EXPLICIT_START
    else:
        assert body_workflow_execution['run_reason'] == WorkflowExecution.RunReason(
                model_workflow_execution.run_reason).name

    if model_workflow_execution.stop_reason is None:
        assert body_workflow_execution['stop_reason'] is None
    else:
        assert body_workflow_execution['stop_reason'] == WorkflowExecution.RunReason(
                model_workflow_execution.stop_reason).name


def validate_serialized_workflow_execution(body_workflow_execution: dict[str, Any],
        model_workflow_execution: WorkflowExecution,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    validate_serialized_workflow_execution_summary(body_workflow_execution,
            model_workflow_execution, context=context)

    workflow_dict = NameAndUuidSerializer(
            model_workflow_execution.workflow, context=context,
            view_name='workflows-detail').data

    verify_name_uuid_url_match(body_workflow_execution['workflow'],
            workflow_dict)

    if model_workflow_execution.started_by is None:
        assert body_workflow_execution['started_by'] is None
    else:
        assert body_workflow_execution['started_by'] == \
                model_workflow_execution.started_by.username

    if model_workflow_execution.marked_done_by is None:
        assert body_workflow_execution['marked_done_by'] is None
    else:
        body_workflow_execution['marked_done_by'] == model_workflow_execution \
                .marked_done_by.username

    if model_workflow_execution.killed_by is None:
        assert body_workflow_execution['killed_by'] is None
    else:
        body_workflow_execution['killed_by'] == model_workflow_execution \
                .killed_by.username


def ensure_serialized_event_valid(response_dict: dict[str, Any],
        event: Event, user: User,
        group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> None:
    context = context_with_authenticated_request(user=user,
            group=event.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    # Use the appropriate serializer based on event type
    if isinstance(event, TaskExecutionStatusChangeEvent):
        serializer_class = TaskExecutionStatusChangeEventSerializer
    elif isinstance(event, WorkflowExecutionStatusChangeEvent):
        serializer_class = WorkflowExecutionStatusChangeEventSerializer
    elif isinstance(event, InsufficientServiceTaskExecutionsEvent):
        serializer_class = InsufficientServiceTaskExecutionsEventSerializer
    elif isinstance(event, MissingHeartbeatDetectionEvent):
        serializer_class = MissingHeartbeatDetectionEventSerializer
    elif isinstance(event, MissingScheduledTaskExecutionEvent):
        serializer_class = MissingScheduledTaskExecutionEventSerializer
    elif isinstance(event, MissingScheduledWorkflowExecutionEvent):
        serializer_class = MissingScheduledWorkflowExecutionEventSerializer
    elif isinstance(event, BasicEvent):
        serializer_class = BasicEventSerializer
    else:
        serializer_class = EventSerializer

    expected_data = serializer_class(event, context=context).data

    # Verify all fields have expected values
    assert response_dict == expected_data, \
        f"Event serialization mismatch. Response: {response_dict}, Expected: {expected_data}"

    # Verify core Event fields
    assert response_dict['uuid'] == str(event.uuid), \
        f"UUID mismatch: {response_dict['uuid']} != {event.uuid}"

    assert response_dict['event_at'] == iso8601_with_z(event.event_at), \
        f"event_at mismatch: {response_dict['event_at']} != {event.event_at}"

    assert response_dict['detected_at'] == iso8601_with_z(event.detected_at), \
        f"detected_at mismatch: {response_dict['detected_at']} != {event.detected_at}"

    assert response_dict['acknowledged_at'] == iso8601_with_z(event.acknowledged_at), \
        f"acknowledged_at mismatch: {response_dict['acknowledged_at']} != {event.acknowledged_at}"

    # Verify severity (serialized as string label)
    assert 'severity' in response_dict, "severity field missing from response"
    assert isinstance(response_dict['severity'], str), \
        f"severity should be string, got {type(response_dict['severity'])}"

    assert response_dict['error_summary'] == event.error_summary, \
        f"error_summary mismatch: {response_dict['error_summary']} != {event.error_summary}"

    assert response_dict['error_details_message'] == event.error_details_message, \
        f"error_details_message mismatch: {response_dict['error_details_message']} != {event.error_details_message}"

    assert response_dict['source'] == event.source, \
        f"source mismatch: {response_dict['source']} != {event.source}"

    assert response_dict['grouping_key'] == event.grouping_key, \
        f"grouping_key mismatch: {response_dict['grouping_key']} != {event.grouping_key}"

    assert response_dict['details'] == event.details, \
        f"details mismatch: {response_dict['details']} != {event.details}"

    assert response_dict['resolved_at'] == iso8601_with_z(event.resolved_at), \
        f"resolved_at mismatch: {response_dict['resolved_at']} != {event.resolved_at}"

    # Verify acknowledged_by_user and resolved_by_user are serialized as usernames (or null)
    if event.acknowledged_by_user is None:
        assert response_dict.get('acknowledged_by_user') is None, \
            f"acknowledged_by_user should be null when model has none: {response_dict.get('acknowledged_by_user')}"
    else:
        assert response_dict.get('acknowledged_by_user') == event.acknowledged_by_user.username, \
            f"acknowledged_by_user mismatch: {response_dict.get('acknowledged_by_user')} != {event.acknowledged_by_user.username}"

    if event.resolved_by_user is None:
        assert response_dict.get('resolved_by_user') is None, \
            f"resolved_by_user should be null when model has none: {response_dict.get('resolved_by_user')}"
    else:
        assert response_dict.get('resolved_by_user') == event.resolved_by_user.username, \
            f"resolved_by_user mismatch: {response_dict.get('resolved_by_user')} != {event.resolved_by_user.username}"

    # Verify event_type is properly set
    assert 'event_type' in response_dict, "event_type field missing from response"
    assert isinstance(response_dict['event_type'], str), \
        f"event_type should be string, got {type(response_dict['event_type'])}"

    # Verify created_by_group (GroupSerializer uses 'id', not 'uuid')
    assert 'created_by_group' in response_dict, "created_by_group field missing from response"
    if event.created_by_group:
        assert response_dict['created_by_group']['id'] == event.created_by_group.id, \
            f"created_by_group id mismatch: {response_dict['created_by_group']['id']} != {event.created_by_group.id}"
        assert response_dict['created_by_group']['name'] == event.created_by_group.name, \
            f"created_by_group name mismatch"

    assert 'created_by_user' in response_dict, "created_by_user field missing from response"
    if event.created_by_user is None:
        assert response_dict['created_by_user'] is None
    else:
        assert response_dict['created_by_user'] == event.created_by_user.username, \
            f"created_by_user id mismatch: {response_dict['created_by_user']} != {event.created_by_user.username}"

    # Verify run_environment if present
    if event.run_environment:
        assert 'run_environment' in response_dict, "run_environment field missing from response"
        assert response_dict['run_environment']['uuid'] == str(event.run_environment.uuid), \
            f"run_environment uuid mismatch"

    # Verify resolved_event if present
    if event.resolved_event:
        assert 'resolved_event' in response_dict, "resolved_event field missing from response"
        assert response_dict['resolved_event']['uuid'] == str(event.resolved_event.uuid), \
            f"resolved_event uuid mismatch"
