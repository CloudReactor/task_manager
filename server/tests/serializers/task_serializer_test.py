from conftest import *

from processes.common.request_helpers import context_with_request
from processes.models import Task
from processes.serializers import TaskSerializer

import pytest

from moto import mock_ecs, mock_sts, mock_events


@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_basic_task_serialization(task_factory):
    task = cast(Task, task_factory())
    context = context_with_request()
    data = TaskSerializer(task, context=context).data
    validate_serialized_task(data, task)


@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_task_serialization_with_unsupported_emcd(task_factory):
    task = cast(Task, task_factory())
    task.execution_method_type = 'Voodoo'
    task.execution_method_capability_details = {
        'witch_id': 'DOLLY76'
    }

    context = context_with_authenticated_request(
        user=task.created_by_user,
        group=task.created_by_group
    )

    data = TaskSerializer(task, context=context).data
    validate_serialized_task(data, task)

    del data['uuid']

    ser = TaskSerializer(data=data, context=context)

    assert ser.is_valid() is True
    assert not ser.errors
    validated = ser.validated_data
    assert validated['execution_method_capability_details'] == task.execution_method_capability_details


@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_basic_task_deserialization(user_factory, run_environment_factory):
    user = user_factory()
    group = user.groups.all()[0]
    run_environment = run_environment_factory(created_by_group=group,
        created_by_user=user)
    context = context_with_authenticated_request(
        user=user,
        group=group,
        api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        api_key_run_environment=run_environment)

    data = {
        'name': 'A Task',
        'description': 'Does something',
        'project_url': 'https://github.com/ExampleOrg/hello',
        'max_age_seconds': 1800,
        'heartbeat_interval_seconds': 600,
        'allocated_cpu_units': 1024,
        'allocated_memory_mb': 2048,
        'run_environment': {
          'name': run_environment.name
        },
        'execution_method_type': 'AWS ECS',
        'execution_method_capability_details': {
            'task_definition_arn': 'arn:aws:ecs:us-west-2:123456789012:task-definition/hello_world:8',
            'default_launch_type': 'FARGATE',
            'supported_launch_types': ['FARGATE'],
            'main_container_name': 'hello',
            'execution_role': 'arn:aws:iam::123456789012:role/execution',
            'task_role': 'arn:aws:iam::123456789012:role/task'
        },
        'infrastructure_type': 'AWS',
        'infrastructure_settings': {
            'network': {
                'subnets': ['subnet1', 'subnet2'],
                'security_groups': ['sg1', 'sg2'],
            },
            'tags': {
                'TagA': 'A',
                'TagB': 'B'
            }
        },
        'log_query': '/aws/fargate/hello_world',
        'links': [
            {
                'name': 'Rollbar',
                'link_url_template': 'https://www.rollbar.com/MyCorp/hello'
            }
        ]
    }

    ser = TaskSerializer(data=data.copy(), context=context)
    ser.is_valid(raise_exception=True)
    task = ser.save()

    for attr in ['name', 'description', 'project_url', 'max_age_seconds',
            'heartbeat_interval_seconds', 'log_query',
            'allocated_cpu_units', 'allocated_memory_mb',
            'execution_method_type', 'infrastructure_type']:
        assert getattr(task, attr) == data[attr]

    assert task.run_environment.uuid == run_environment.uuid

    emcd = data['execution_method_capability_details']

    for attr in ['task_definition_arn', 'default_launch_type',
            'supported_launch_types', 'main_container_name',]:
        assert getattr(task, 'aws_ecs_' + attr) == emcd[attr]

    for attr in ['execution_role', 'task_role',]:
        assert getattr(task, 'aws_ecs_default_' + attr) == emcd[attr]

    aws_network = data['infrastructure_settings']['network']

    assert task.aws_default_subnets == aws_network['subnets']
    assert task.aws_ecs_default_security_groups == aws_network['security_groups']


@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_legacy_task_deserialization(user_factory, run_environment_factory):
    user = user_factory()
    group = user.groups.all()[0]
    run_environment = run_environment_factory(created_by_group=group,
        created_by_user=user)
    context = context_with_authenticated_request(
        user=user,
        group=group,
        api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        api_key_run_environment=run_environment)

    data = {
        'name': 'A Task',
        'description': 'Does something',
        'project_url': 'https://github.com/ExampleOrg/hello',
        'max_age_seconds': 1800,
        'heartbeat_interval_seconds': 600,
        'run_environment': {
          'name': run_environment.name
        },
        'execution_method_capability': {
            'type': 'AWS ECS',
            'task_definition_arn': 'arn:aws:ecs:us-west-2:123456789012:task-definition/hello_world:8',
            'default_launch_type': 'FARGATE',
            'supported_launch_types': ['FARGATE'],
            'main_container_name': 'hello',
            'allocated_cpu_units': 1024,
            'allocated_memory_mb': 2048,
            'default_execution_role': 'arn:aws:iam::123456789012:role/execution',
            'default_task_role': 'arn:aws:iam::123456789012:role/task',
            'default_subnets': ['subnet1', 'subnet2'],
            'default_security_groups': ['sg1', 'sg2'],
            'tags': {
                'TagA': 'A',
                'TagB': 'B'
            },
        },
        'log_query': '/aws/fargate/hello_world',
        'links': [
            {
                'name': 'Rollbar',
                'link_url_template': 'https://www.rollbar.com/MyCorp/hello'
            }
        ]
    }

    ser = TaskSerializer(data=data.copy(), context=context)
    ser.is_valid(raise_exception=True)
    task = ser.save()

    for attr in ['name', 'description', 'project_url', 'max_age_seconds',
            'heartbeat_interval_seconds', 'log_query']:
        assert getattr(task, attr) == data[attr]

    assert task.run_environment.uuid == run_environment.uuid

    emc = data['execution_method_capability']
    assert task.aws_default_subnets == emc['default_subnets']

    for attr in ['task_definition_arn', 'default_launch_type',
            'supported_launch_types', 'main_container_name',
            'default_execution_role', 'default_task_role',
            'default_security_groups']:
        assert getattr(task, 'aws_ecs_' + attr) == emc[attr]

    for attr in ['allocated_cpu_units', 'allocated_memory_mb']:
        assert getattr(task, attr) == emc[attr]
