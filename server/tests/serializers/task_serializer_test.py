from rest_framework.exceptions import APIException

from processes.common.aws import extract_cluster_name
from processes.common.request_helpers import context_with_request
from processes.models import Task
from processes.serializers import TaskSerializer

import pytest

from moto import mock_aws
from conftest import *


@pytest.mark.django_db
@mock_aws
def test_basic_task_serialization(task_factory):
    task = cast(Task, task_factory())
    context = context_with_request()
    data = TaskSerializer(task, context=context).data
    validate_serialized_task(data, task)


@pytest.mark.django_db
@mock_aws
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


@mock_aws
@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_legacy_schema, is_service, is_scheduled
""", [
    (False, False, False),

    # Service property extraction into legacy columns not supported
    # (False, True, False),

    (False, False, True),
    (True, False, False),
    (True, True, False),
    (True, False, True),
])
def test_aws_ecs_task_deserialization(is_legacy_schema: bool,
        is_service: bool, is_scheduled: bool,
        user_factory, run_environment_factory):
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

    schedule = ''
    if is_scheduled:
        schedule = 'cron(9 0 * * ? *)'

    data = make_aws_ecs_task_request_body(
            run_environment=run_environment,
            aws_ecs_setup=aws_ecs_setup,
            is_service=is_service,
            schedule=schedule,
            is_legacy_schema=is_legacy_schema)

    ser = TaskSerializer(data=data.copy(), context=context)
    ser.is_valid(raise_exception=True)
    task = ser.save()

    validate_saved_task(body_task=data, model_task=task, context=context)

    reserialized_data = TaskSerializer(task, context=context).data
    validate_serialized_task(reserialized_data, task)


@mock_aws
@pytest.mark.django_db
@pytest.mark.parametrize("""
  api_key_access_level, is_api_key_scoped,
  run_environment_send_type,
  status_code, validation_error_attribute,
""", [
    (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
    SEND_ID_CORRECT,
    200, None),
    (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
    SEND_ID_OTHER,
    403, None),
    (UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, True,
    SEND_ID_CORRECT,
    403, None),
    (UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, True,
    SEND_ID_CORRECT,
    403, None),
    (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
    SEND_ID_CORRECT,
    200, None),
    (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
    SEND_ID_OTHER,
    200, None),
    (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
    SEND_ID_IN_WRONG_GROUP,
    422, 'run_environment'),
    (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
    SEND_ID_IN_WRONG_GROUP,
    422, 'run_environment'),
    (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
    SEND_ID_WRONG,
    422, 'run_environment'),
    (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
    SEND_ID_WRONG,
    422, 'run_environment'),
])
def test_task_deserialization_with_existing_task(
    api_key_access_level: int, is_api_key_scoped: bool,
    run_environment_send_type: str,
    status_code: int, validation_error_attribute: Optional[str],
    unknown_task_factory, run_environment_factory,
    user_factory):
    user = user_factory()
    group = user.groups.all()[0]
    run_environment = run_environment_factory(
        created_by_group=group,
        created_by_user=user)

    task = cast(Task, unknown_task_factory(
        run_environment=run_environment,
        created_by_group=group,
        created_by_user=user))

    context = context_with_authenticated_request(
        user=user, group=group,
        api_key_access_level=api_key_access_level,
        api_key_run_environment=run_environment if is_api_key_scoped else None)

    if run_environment_send_type == SEND_ID_OTHER:
        run_environment = run_environment_factory(
            created_by_group=group,
            created_by_user=user)
    elif run_environment_send_type == SEND_ID_IN_WRONG_GROUP:
        run_environment = run_environment_factory()
    elif run_environment_send_type == SEND_ID_WRONG:
        run_environment = RunEnvironment(name='Unsaved')

    data = make_unknown_task_request_body(
            run_environment=run_environment)

    ser = TaskSerializer(task, data=data.copy(), context=context)

    try:
        ser.is_valid(raise_exception=True)
        ser.save()
    except APIException as ex:
        assert ex.status_code == status_code
        if validation_error_attribute:
            assert isinstance(ex.detail, dict)
            assert validation_error_attribute == list(ex.detail.keys())[0]
    else:
        assert status_code == 200
        assert validation_error_attribute is None
