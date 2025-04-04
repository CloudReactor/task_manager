from conftest import *

from processes.common.request_helpers import context_with_request
from processes.models import TaskExecution
from processes.serializers import TaskExecutionSerializer

import pytest

from moto import mock_aws
@pytest.mark.django_db
@mock_aws
def test_basic_task_execution_serialization(task_execution_factory):
    task_execution = cast(TaskExecution, task_execution_factory())
    context = context_with_request()
    data = TaskExecutionSerializer(task_execution, context=context).data
    validate_serialized_task_execution(data, task_execution)


@pytest.mark.django_db
@mock_aws
def test_task_execution_in_workflow_serialization(task_execution_factory,
        workflow_task_instance_execution_factory):
    task_execution = cast(TaskExecution, task_execution_factory())

    wtie = workflow_task_instance_execution_factory(
        task_execution=task_execution)

    context = context_with_request()
    data = TaskExecutionSerializer(task_execution, context=context).data

    validate_serialized_task_execution(data, task_execution)

    assert data['workflow_task_instance_execution']['uuid'] == str(wtie.uuid)


@mock_aws
@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_passive, is_legacy_schema
""", [
  (False, False),
  (False, True),
  (True, False),
  (True, True),
])
def test_auto_created_aws_ecs_task_execution_deserialization(
        is_passive: bool, is_legacy_schema: bool,
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory):
    user = user_factory()
    group = user.groups.all()[0]
    run_environment = run_environment_factory(
        created_by_group=group,
        created_by_user=user)
    context = context_with_authenticated_request(
        user=user,
        group=group,
        api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        api_key_run_environment=run_environment)

    aws_ecs_setup = setup_aws_ecs(run_environment=run_environment)

    request_body = make_aws_ecs_task_execution_request_body(
        run_environment=run_environment,
        run_environment_factory=run_environment_factory,
        group_factory=group_factory,
        task_factory=task_factory,
        task_execution_factory=task_execution_factory,
        user=user,
        was_auto_created=True, is_passive=is_passive,
        aws_ecs_setup=aws_ecs_setup,
        is_legacy_schema=is_legacy_schema)

    ser = TaskExecutionSerializer(data=request_body.copy(), context=context)
    ser.is_valid(raise_exception=True)
    task_execution = ser.save()

    validate_saved_task_execution(body_task_execution=request_body,
        model_task_execution=task_execution, context=context)

    reserialized_data = TaskExecutionSerializer(task_execution,
            context=context).data
    validate_serialized_task_execution(reserialized_data, task_execution)


@pytest.mark.django_db
def test_unsupported_execution_method_task_execution_deserialization(
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory):
    user = user_factory()
    group = user.groups.all()[0]
    run_environment = run_environment_factory(
        created_by_group=group,
        created_by_user=user)
    context = context_with_authenticated_request(
        user=user,
        group=group,
        api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        api_key_run_environment=run_environment)


    request_body = make_task_execution_request_body(
        uuid_send_type = SEND_ID_NONE,
        task_send_type = SEND_ID_CORRECT,
        user = user,
        api_key_run_environment = run_environment,
        group_factory = group_factory,
        run_environment_factory = run_environment_factory,
        task_factory = task_factory,
        task_execution_factory = task_execution_factory
    )

    task_request_fragment = request_body['task']
    task_request_fragment['execution_method_type'] = 'RANDO_METHOD'
    task_request_fragment['execution_method_capability_details'] = {
      'a': 2
    }
    task_request_fragment['infrastructure_type'] = 'NOTAWESOME'
    task_request_fragment['infrastructure_settings'] = {
        'c': ['x', 'y']
    }

    request_body['execution_method_type'] = 'RANDO_METHOD'
    task_request_fragment['execution_method_details'] = {
        'b': 3
    }
    request_body['infrastructure_type'] = 'NOTAWESOME'
    request_body['infrastructure_settings'] = {
        'c': ['x', 'z']
    }

    ser = TaskExecutionSerializer(data=request_body.copy(), context=context)
    ser.is_valid(raise_exception=True)
    task_execution = ser.save()

    validate_saved_task_execution(body_task_execution=request_body,
        model_task_execution=task_execution, context=context)

    reserialized_data = TaskExecutionSerializer(task_execution,
            context=context).data
    validate_serialized_task_execution(reserialized_data, task_execution)
