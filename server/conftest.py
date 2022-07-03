from collections import abc
from datetime import datetime
from typing import cast, Any, List, Optional, Mapping, NamedTuple, Tuple

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
from processes.execution_methods import AwsSettings, AwsEcsServiceSettings
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
    UnknownExecutionMethodTaskFactory,
    TaskExecutionFactory,
    WorkflowFactory,
    WorkflowTaskInstanceFactory,
    WorkflowTransitionFactory,
    WorkflowExecutionFactory,
    WorkflowTaskInstanceExecutionFactory,
    PagerDutyProfileFactory,
    EmailNotificationProfileFactory,
    AlertMethodFactory
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
register(UnknownExecutionMethodTaskFactory)
register(TaskExecutionFactory)
register(WorkflowFactory)
register(WorkflowTaskInstanceFactory)
register(WorkflowTransitionFactory)
register(WorkflowExecutionFactory)
register(WorkflowTaskInstanceExecutionFactory)
register(PagerDutyProfileFactory)
register(EmailNotificationProfileFactory)
register(AlertMethodFactory)


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
    header = cast(List[str], settings.SIMPLE_JWT['AUTH_HEADER_TYPES'])[0]
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


def assert_deep_subset(subset: Any, superset: Any) -> None:
    if isinstance(subset, str): # Because string is iterable
        assert subset == superset
    elif isinstance(subset, abc.Mapping):
        assert isinstance(superset, abc.Mapping)
        for k, v in subset.items():
            assert k in superset
            assert_deep_subset(v, superset[k])
    elif isinstance(subset, abc.Iterable):
        assert isinstance(superset, abc.Iterable)
        assert len(subset) == len(superset)

        for i, v in enumerate(subset):
            assert_deep_subset(v, superset[i])
    else:
        assert subset == superset


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
    'should_clear_failure_alerts_on_success',
    'should_clear_timeout_alerts_on_success',
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
    'execution_method_type', 'scheduling_provider_type',
    'service_provider_type',
] + EXECUTABLE_ATTRIBUTES

ENHANCED_TASK_ATTRIBUTES = [
   'execution_method_capability_details',
   'infrastructure_settings',
   'scheduling_settings',
   'service_settings',
]

OUTPUT_TASK_ATTRIBUTES = COPIED_TASK_ATTRIBUTES + ENHANCED_TASK_ATTRIBUTES + [
   'uuid', 'dashboard_url', 'infrastructure_website_url', 'logs_url',
   'created_at', 'updated_at',
]


def make_common_task_request_body(run_environment_name='Staging') -> dict[str, Any]:
    return {
        'name': 'A Task',
        'description': 'Does something',
        'project_url': 'https://github.com/ExampleOrg/hello',
        'max_age_seconds': 1800,
        'heartbeat_interval_seconds': 600,
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


class AwsEcsSetup(NamedTuple):
    cluster: Mapping[str, Any]
    task_definition: Mapping[str, Any]

    @property
    def task_definition_arn(self) -> str:
        return cast(str, self.task_definition['taskDefinitionArn'])

def setup_aws_ecs(run_environment: RunEnvironment) -> AwsEcsSetup:
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
        task_definition=task_def_response['taskDefinition'])


def make_aws_ecs_task_request_body(run_environment: RunEnvironment,
        task_definition_arn: Optional[str] = None,
        is_service=False, schedule='',
        is_legacy_schema=False) -> dict[str, Any]:
    body = make_common_task_request_body(
            run_environment_name=run_environment.name)

    body['schedule'] = schedule

    if is_service:
        body['service_instance_count'] = 1

    task_definition_arn = task_definition_arn or 'arn:aws:ecs:us-west-1:123456789012:task-definition/hello_world:8'

    if is_legacy_schema:
        body['execution_method_capability'] = {
            'type': 'AWS ECS',
            'task_definition_arn': task_definition_arn,
            'default_launch_type': 'FARGATE',
            'supported_launch_types': ['FARGATE'],
            'main_container_name': 'hello',
            'allocated_cpu_units': 1024,
            'allocated_memory_mb': 2048,
            'default_execution_role': run_environment.aws_ecs_default_execution_role,
            'default_task_role': 'arn:aws:iam::123456789012:role/task',
            'default_subnets': ['subnet1', 'subnet2'],
            'default_security_groups': ['sg1', 'sg2'],
            'tags': {
                'TagA': 'A',
                'TagB': 'B'
            },
        }

        if is_service:
            body['execution_method_capability']['service_options'] = {
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
    else:
        body['allocated_cpu_units'] = 1024
        body['allocated_memory_mb'] = 2048
        body['execution_method_type'] = 'AWS ECS'
        body['execution_method_capability_details'] = {
            'task_definition_arn': task_definition_arn,
            'default_launch_type': 'FARGATE',
            'supported_launch_types': ['FARGATE'],
            'main_container_name': 'hello',
            'execution_role': run_environment.aws_ecs_default_execution_role,
            'task_role': 'arn:aws:iam::123456789012:role/task'
        }
        body['infrastructure_type'] = 'AWS'
        body['infrastructure_settings'] = {
            'network': {
                'subnets': ['subnet1', 'subnet2'],
                'security_groups': ['sg1', 'sg2'],
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
            body['service_provider_type'] = 'AWS ECS'
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
            assert_deep_subset(body_task[attr], getattr(model_task, attr))

    emcd = body_task.get('execution_method_capability_details')

    if emcd is not None:
        # Check that deprecated columns are populated
        for attr in ['task_definition_arn', 'default_launch_type',
                'supported_launch_types', 'main_container_name',]:
            if attr in emcd:
                assert getattr(model_task, 'aws_ecs_' + attr) == emcd[attr]

        for attr in ['execution_role', 'task_role',]:
            if attr in emcd:
                assert getattr(model_task, 'aws_ecs_default_' + attr) == emcd[attr]

        # End check that deprecated columns are populated

        infra = body_task.get('infrastructure_settings')

        if infra is not None:
            model_infra = AwsSettings.parse_obj(model_task.infrastructure_settings)

            ensure_attributes_match(infra, model_infra,
                    ['tags'], partial=True)

            aws_network = infra.get('network')
            if aws_network is not None:
                model_network = model_infra.network
                ensure_attributes_match(aws_network, model_network,
                        COPIED_AWS_NETWORK_ATTRIBUTES, partial=True)

                if 'subnets' in aws_network:
                    assert model_network.subnet_infrastructure_website_urls is not None
                    assert len(model_network.subnet_infrastructure_website_urls) == len(aws_network['subnets'])
                    for i, subnet in enumerate(aws_network['subnets']):
                        assert model_network.subnet_infrastructure_website_urls[i].index(subnet) >= 0

                if 'security_groups' in aws_network:
                    assert model_network.security_group_infrastructure_website_urls is not None
                    assert len(model_network.security_group_infrastructure_website_urls) == len(aws_network['security_groups'])
                    for i, subnet in enumerate(aws_network['security_groups']):
                        assert model_network.security_group_infrastructure_website_urls[i].index(subnet) >= 0

            aws_logging = infra.get('logging')
            if aws_logging is not None:
                model_logging = model_infra.logging
                ensure_attributes_match(aws_network, model_logging,
                        ['driver'], partial=True)

                log_options = aws_logging.get('options')
                if log_options is not None:
                    ensure_attributes_match(log_options, model_logging.options,
                        ['group', 'region', 'stream_prefix'], partial=True)

                if (aws_logging.get('driver') == 'awslogs') and ('group' in aws_logging):
                    assert model_logging.infrastructure_website_url is not None

        body_service_settings = body_task.get('service_settings')

        if body_service_settings is None:
            assert model_task.service_provider_type == ''
            assert model_task.service_settings is None
        else:
            assert model_task.service_provider_type == body_task['service_provider_type']
            model_service_settings = model_task.service_settings
            assert model_service_settings is not None

            model_service_settings = AwsEcsServiceSettings.parse_obj(model_task.service_settings)

            ensure_attributes_match(body_service_settings, model_service_settings, [
                'scheduling_strategy', 'force_new_deployment',
                'enable_ecs_managed_tags', 'propagate_tags', 'tags',
            ], partial=True)


    if body_task.get('schedule'):
        assert model_task.scheduling_provider_type == 'AWS CloudWatch'
        assert model_task.scheduling_settings is not None
    else:
        assert model_task.scheduling_provider_type == ''
        assert model_task.scheduling_settings is None

    # Deprecated schema
    emc = body_task.get('execution_method_capability')
    if emc is not None:
        for attr in ['allocated_cpu_units', 'allocated_memory_mb']:
            if attr in emc:
                assert getattr(model_task, attr) == emc[attr]

        model_infra = AwsSettings.parse_obj(model_task.infrastructure_settings)
        model_network = model_infra.network

        if 'default_subnets' in emc:
            assert model_task.aws_default_subnets == emc['default_subnets']
            assert model_network.subnet_infrastructure_website_urls is not None
            assert len(model_network.subnet_infrastructure_website_urls) == len(emc['default_subnets'])
            for i, subnet in enumerate(emc['default_subnets']):
                assert model_network.subnet_infrastructure_website_urls[i].index(subnet) >= 0

        if 'default_security_groups' in emc:
            assert model_task.aws_ecs_default_security_groups == emc['default_security_groups']
            assert model_network.security_group_infrastructure_website_urls is not None
            assert len(model_network.security_group_infrastructure_website_urls) == len(emc['default_security_groups'])
            for i, security_group in enumerate(emc['default_security_groups']):
                assert model_network.security_group_infrastructure_website_urls[i].index(security_group) >= 0

        for attr in ['task_definition_arn', 'default_launch_type',
                'supported_launch_types', 'main_container_name',
                'default_execution_role', 'default_task_role',
                'default_security_groups']:
            if attr in emc:
                assert getattr(model_task, 'aws_ecs_' + attr) == emc[attr]

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
            for attr in nullable_service_attrs:
                assert getattr(model_task, 'aws_ecs_service_' + attr) is None

            assert not AwsEcsServiceLoadBalancerDetails.objects.filter(
                    task__id=model_task.id).exists()

            assert model_task.aws_ecs_service_propagate_tags == ''

            assert model_task.service_provider_type == ''
            assert model_task.service_settings is None
        else:
            assert model_task.service_instance_count >= 1
            for attr in nullable_service_attrs:
                if attr in service_options:
                    assert getattr(model_task, 'aws_ecs_service_' + attr) == service_options[attr]

            assert getattr(model_task, 'aws_ecs_service_propagate_tags') == \
                    service_options.get('propagate_tags') or ''

            assert model_task.service_provider_type == 'AWS ECS'
            assert model_task.service_settings is not None

            lb_settings = service_options.get('load_balancers')
            model_lbs = AwsEcsServiceLoadBalancerDetails.objects.filter(
                    task__id=model_task.id).all()

            if lb_settings:
                assert len(model_lbs) == len(lb_settings)

                for lb in lb_settings:
                    model_lb = [x for x in model_lbs if x.target_group_arn == lb['target_group_arn']][0]
                    assert model_lb is not None
                    ensure_attributes_match(lb, model_lb,
                        ['container_name', 'container_port'])
            else:
                assert len(model_lbs) == 0



def validate_serialized_task_execution(body_task_execution: dict[str, Any],
        model_task_execution: TaskExecution,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_task_execution, model_task_execution, [
        'uuid', 'dashboard_url', 'infrastructure_website_url',
        'task_version_number', 'task_version_text',
        'task_version_signature', 'commit_url',
        'other_instance_metadata',
        'hostname',
        'environment_variables_overrides',
        'started_at',
        'finished_at',
        'marked_done_at',
        'marked_outdated_at',
        'kill_started_at', 'kill_finished_at',
        'kill_error_code',
        'last_heartbeat_at',
        'failed_attempts', 'timed_out_attempts',
        'exit_code', 'last_status_message',
        'error_count', 'skipped_count',
        'expected_count', 'success_count',
        'other_runtime_metadata',
        'current_cpu_units', 'mean_cpu_units', 'max_cpu_units',
        'current_memory_mb', 'mean_memory_mb', 'max_memory_mb',
        'wrapper_version', 'wrapper_log_level',
        'deployment', 'process_command', 'is_service',
        'task_max_concurrency', 'max_conflicting_age_seconds',
        'prevent_offline_execution',
        'process_timeout_seconds', 'process_termination_grace_period_seconds',
        'process_max_retries', 'process_retry_delay_seconds',
        'schedule',
        'heartbeat_interval_seconds',
        'api_base_url', # Don't expose api_key
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
        'created_at', 'updated_at',
    ])

    task_dict = NameAndUuidSerializer(
            model_task_execution.task, context=context,
            view_name='tasks-detail').data

    verify_name_uuid_url_match(body_task_execution['task'],
            task_dict)

    assert body_task_execution['status'] == TaskExecution.Status(
            model_task_execution.status).name

    assert body_task_execution['started_by'] == model_task_execution \
            .started_by.username

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

    assert body_workflow_execution['status'] == WorkflowExecution.Status(
            model_workflow_execution.status).name

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

    assert body_workflow_execution['started_by'] == model_workflow_execution \
            .started_by.username

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
