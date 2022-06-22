from typing import Any, List, Optional, Tuple, cast

from datetime import timedelta
import random
import uuid
from urllib.parse import quote

from django.utils import timezone

from django.contrib.auth.models import User

from processes.execution_methods.unknown_execution_method import UnknownExecutionMethod

from processes.models import (
    UserGroupAccessLevel, Subscription, RunEnvironment,
    Task, TaskExecution
)

import pytest

from rest_framework.test import APIClient

from moto import mock_ecs, mock_sts, mock_events

from conftest import *


def ensure_serialized_task_execution_valid(
        response_task_execution: dict[str, Any], task_execution: TaskExecution,
        user: User, group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> None:
    context = context_with_authenticated_request(user=user,
            group=task_execution.task.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    validate_serialized_task_execution(response_task_execution,
            task_execution, context=context)

    if api_key_run_environment:
        assert api_key_run_environment.pk == task_execution.task.run_environment.pk

@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  user_has_another_group, send_group_id_type, send_task_uuid_type,
  status_code, expected_indices
""", [
  # Admin with Admin API key, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_CORRECT, SEND_ID_NONE,
   200, [0, 1]),

  # Admin with Admin API key, no explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_NONE, SEND_ID_NONE,
   200, [0, 1]),

  # Observer with JWT token, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   False, SEND_ID_CORRECT, SEND_ID_NONE,
   200, [0, 1]),

  # Observer in single group with JWT token, no explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   False, SEND_ID_NONE, SEND_ID_NONE,
   200, [0, 1]),

  # Admin in multiple groups with JWT token, no explicit group yields 400
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   True, SEND_ID_NONE, SEND_ID_NONE,
   400, None),

  # Developer in multiple groups with JWT token, explicit group yields 200
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   True, SEND_ID_CORRECT, SEND_ID_NONE,
   200, [0, 1]),

  # Support user in multiple groups with JWT token, explicit Task yields 200
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   True, SEND_ID_NONE, SEND_ID_CORRECT,
   200, [0]),

  # Admin with Observer API key, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   False, SEND_ID_CORRECT, SEND_ID_NONE,
   200, [0, 1]),

  # Admin with multiple groups with Observer API key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   True, SEND_ID_CORRECT, SEND_ID_NONE,
   200, [0, 1]),

  # No API key with no explicit group in request yields 400
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   True, SEND_ID_NONE, SEND_ID_NONE,
   400, None),

  # API key with no explicit group in request succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   True, SEND_ID_NONE, SEND_ID_NONE,
   200, [0, 1]),

  # Admin with Admin API key, explicit wrong group yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_WRONG, SEND_ID_NONE,
   422, None),

  # Admin using JWT, explicit wrong group yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   False, SEND_ID_WRONG, SEND_ID_NONE,
   422, None),

  # Admin using Admin API key, explicit bad group ID yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_NOT_FOUND, SEND_ID_NONE,
   422, None),

  # Admin using JWT, explicit bad group ID yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   False, SEND_ID_NOT_FOUND, SEND_ID_NONE,
   422, None),

  # Admin with Admin API key scoped to correct Run Environment, explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_CORRECT,
   False, SEND_ID_CORRECT, SEND_ID_NONE,
   200, [0]),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   False, SEND_ID_CORRECT, SEND_ID_NONE,
   401, None),

  # TODO: check filtering, non-default ordering
])
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_list(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        user_has_another_group: bool, send_group_id_type: str,
        send_task_uuid_type: str,
        status_code: int, expected_indices: List[int],
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory, api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    another_group = group_factory()

    if user_has_another_group:
        set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    task_group = group

    production_run_environment = run_environment_factory(created_by_group=task_group)
    production_task = task_factory(created_by_group=task_group,
        run_environment=production_run_environment)

    test_run_environment = run_environment_factory(created_by_group=task_group)
    test_task = task_factory(created_by_group=task_group,
        run_environment=test_run_environment)

    task_executions = [
      task_execution_factory(task=production_task),
      task_execution_factory(task=test_task)
    ]

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = production_run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = test_run_environment

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    params = {}

    group_id: Optional[str] = None

    if send_group_id_type == SEND_ID_CORRECT:
        group_id = str(group.id)
    elif send_group_id_type == SEND_ID_NOT_FOUND:
        group_id = '666'
    elif send_group_id_type == SEND_ID_WRONG:
        group_id = str(another_group.id)

    if group_id:
        params['task__created_by_group__id'] = group_id

    task_uuid: Optional[str] = None


    if send_task_uuid_type == SEND_ID_CORRECT:
        task_uuid = str(production_task.uuid)
    elif send_task_uuid_type == SEND_ID_NOT_FOUND:
        task_uuid = 'abc'

    if task_uuid:
        params['task__uuid'] = task_uuid

    response = client.get('/api/v1/task_executions/', params)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        page = response.data
        assert page['count'] == len(expected_indices)
        results = page['results']

        for i in expected_indices:
            response_task_execution = results[i]
            target_task_execution = task_executions[expected_indices[i]]
            ensure_serialized_task_execution_valid(response_task_execution,
                    task_execution=target_task_execution, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)


def common_setup(is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str,
        user, group_factory, run_environment_factory,
        task_factory, task_execution_factory, api_client) \
        -> Tuple[Optional[TaskExecution], Task, Optional[RunEnvironment], APIClient, str]:
    group = user.groups.first()

    if group_access_level is not None:
        set_group_access_level(user=user, group=group,
                access_level=group_access_level)

    task_execution_group = group

    run_environment = run_environment_factory(created_by_group=task_execution_group)
    another_run_environment = run_environment_factory(created_by_group=task_execution_group)

    task = task_factory(created_by_group=group, run_environment=run_environment)

    task_execution_run_environment = run_environment

    task_execution: Optional[TaskExecution] = None
    if uuid_send_type != SEND_ID_NONE:
        task_execution = task_execution_factory(task=task)

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = task_execution_run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = another_run_environment

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    url = '/api/v1/task_executions/'

    if uuid_send_type != SEND_ID_NONE:
        assert task_execution is not None
        task_execution_uuid = uuid.uuid4()
        if uuid_send_type == SEND_ID_CORRECT:
            task_execution_uuid = task_execution.uuid
        elif uuid_send_type == SEND_ID_IN_WRONG_GROUP:
            another_group = group_factory()
            set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
            task_in_other_group = task_factory(created_by_group=another_group)
            task_execution_in_other_group = task_execution_factory(
                    task=task_in_other_group)
            task_execution_uuid = task_execution_in_other_group.uuid

        url += quote(str(task_execution_uuid)) + '/'

    return (task_execution, task, api_key_run_environment, client, url)


def make_request_body(uuid_send_type: Optional[str],
        task_send_type: Optional[str],
        user: User,
        api_key_run_environment: Optional[RunEnvironment],
        task_execution: Optional[TaskExecution],
        group_factory, run_environment_factory, task_factory,
        task_execution_factory,
        task_execution_status: str = 'RUNNING',
        task_property_name: str = 'task',
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


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  uuid_send_type,
  status_code
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT,
   200),

  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT,
   200),

  # Developer with API Key succeeds with unscoped Alert Method
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT,
   200),

  # Observer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT,
   200),

  # Admin with API Key with support access succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT,
   200),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT,
   200),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT,
   200),

  # Observer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   SEND_ID_CORRECT,
   200),

  # Developer with developer API key scoped to correct Run Environment,
  # explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT,
   200),

  # Developer with developer API key scoped to different Run Environment gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT,
   404),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_NONE,
   SEND_ID_NOT_FOUND,
   404),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_NONE,
   SEND_ID_IN_WRONG_GROUP,
   404),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT,
   401),
])
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_fetch(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory, task_factory,
        task_execution_factory, api_client) -> None:
    user = user_factory()
    task_execution, _task, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    response = client.get(url)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        ensure_serialized_task_execution_valid(response_task_execution=response.data,
          task_execution=task_execution, user=user,
          group_access_level=group_access_level,
          api_key_access_level=api_key_access_level,
          api_key_run_environment=api_key_run_environment)


@pytest.mark.django_db
@pytest.mark.parametrize("""
    is_authenticated, group_access_level,
    api_key_access_level, api_key_scope_type,
    body_uuid_type, task_send_type, task_execution_status,
    status_code, validation_error_attribute, error_code
""", [
    # Task with API Key succeeds
    (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
    UserGroupAccessLevel.ACCESS_LEVEL_TASK, None,
    SEND_ID_NONE, SEND_ID_CORRECT, 'RUNNING',
    201, None, None),

    # Developer with unscoped API Key fails with 400 when Task is
    # specifically empty
    (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
    UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
    SEND_ID_NONE, SEND_ID_NONE, 'RUNNING',
    400, 'task', 'null'),

    # Task with unscoped API Key succeeds when Task is specified, status is RUNNING
    (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
    UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_NONE,
    SEND_ID_NONE, SEND_ID_CORRECT, 'RUNNING',
    201, None, None),

    # Task with unscoped API Key succeeds when Task is specified, status is MANUALLY_STARTED
    (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
    UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_NONE,
    SEND_ID_NONE, SEND_ID_CORRECT, 'MANUALLY_STARTED',
    201, None, None),

    # non-existent uuid is present in request body, status is RUNNING
    (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
    UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
    SEND_ID_NOT_FOUND, SEND_ID_CORRECT, 'RUNNING',
    400, 'uuid', 'not_allowed'),

    # uuid of existing Task Execution is present in request body
    (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
    UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
    SEND_ID_WRONG, SEND_ID_CORRECT, 'RUNNING',
    400, 'uuid', 'not_allowed'),

    # Developer with unscoped API Key cannot attach a Task in the
    # wrong Group
    (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
    UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
    SEND_ID_NONE, SEND_ID_IN_WRONG_GROUP, 'RUNNING',
    422, 'task', 'not_found'),

    # Task with scoped API Key succeeds when Task is scoped
    # with the same Run Environment
    (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
    UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_CORRECT,
    SEND_ID_NONE, SEND_ID_CORRECT, 'MANUALLY_STARTED',
    201, None, None),

    # Developer with scoped API Key fails when Task is omitted, status is MANUALLY_STARTED
    (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
    UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
    SEND_ID_NONE, None, 'MANUALLY_STARTED',
    400, 'task', 'missing'),

    # Developer with scoped API Key fails when Task is omitted, status is RUNNING
    (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
     UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
     SEND_ID_NONE, None, 'RUNNING',
     400, 'task', 'missing'),

    # Developer with scoped API Key cannot create Task Execution with no
    # Task, status is MANUALLY_STARTED
    (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
    UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
    SEND_ID_NONE, SEND_ID_NONE, 'MANUALLY_STARTED',
    400, 'task', 'null'),

    # Developer with scoped API Key cannot create Task Execution with no
    # Task, status is RUNNING
    (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
     UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
     SEND_ID_NONE, SEND_ID_NONE, 'RUNNING',
     400, 'task', 'null'),

    # Developer with scoped API Key cannot create Task Execution with a
    # Task in another Run Environment, status is MANUALLY_STARTED
    (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
    UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
    SEND_ID_NONE, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT, 'MANUALLY_STARTED',
    422, 'task', 'not_found'),

    # Admin with API Key with support access fails with 403
    (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
    UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
    SEND_ID_NONE, SEND_ID_CORRECT, 'RUNNING',
    403, None, None),

    # Support user with API Key with Observer access level fails with 403
    (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
     UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
     SEND_ID_NONE, SEND_ID_CORRECT, 'MANUALLY_STARTED',
     403, None, None),

    # Task with JWT token succeeds
    (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
    None, None,
    SEND_ID_NONE, SEND_ID_CORRECT, 'MANUALLY_STARTED',
    201, None, None),

    # Support user with JWT token succeeds
    (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
    None, None,
    SEND_ID_NONE, SEND_ID_CORRECT, 'MANUALLY_STARTED',
    201, None, None),

    # Observer with JWT token fails with 403
    (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
    None, None,
    SEND_ID_NONE, SEND_ID_CORRECT, 'MANUALLY_STARTED',
    403, None, None),

    # No authentication yields 401
    (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
    None, None,
    SEND_ID_NONE, SEND_ID_CORRECT, 'MANUALLY_STARTED',
    401, None, None),
    ])
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_create_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        body_uuid_type: str, task_send_type: str, task_execution_status: str,
        status_code: int, validation_error_attribute: Optional[str],
        error_code: Optional[str],
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory,
        api_client) -> None:
    """
    This only tests access control to the CREATE endpoint, not the actual changes.
    """

    user = user_factory()

    task_execution, _task, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    request_data = make_request_body(uuid_send_type=body_uuid_type,
            task_send_type=task_send_type,
            task_execution_status=task_execution_status,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            task_execution=task_execution,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory)

    old_count = TaskExecution.objects.count()

    response = client.post(url, data=request_data)

    assert response.status_code == status_code

    new_count = TaskExecution.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1

        response_task_execution = cast(dict[str, Any], response.data)
        task_execution_uuid = response_task_execution['uuid']
        created_am = TaskExecution.objects.get(uuid=task_execution_uuid)

        assert group_access_level is not None
        ensure_serialized_task_execution_valid(response_task_execution=response_task_execution,
                task_execution=created_am, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)
    else:
        assert new_count == old_count
        check_validation_error(response, validation_error_attribute,
                error_code)


@pytest.mark.django_db
@pytest.mark.parametrize("""
    was_auto_created, passive,
    status_code, validation_error_attribute, error_code
""", [
    (True, True, 201, None, None),
    (False, True, 422, 'task', 'not_found'),
    (True, False, 400, 'passive', 'invalid'),
])
def test_task_execution_with_unknown_method_auto_creation(
        was_auto_created, passive,
        status_code, validation_error_attribute, error_code,
        user_factory, group_factory, run_environment_factory,
        unknown_execution_method_task_factory, task_execution_factory,
        api_client) -> None:
    """
    Test auto-creation of Tasks with unknown execution method along with Task Execution
    """

    user = user_factory()

    _task_execution, _task, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_scope_type=SCOPE_TYPE_CORRECT,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=unknown_execution_method_task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    assert api_key_run_environment is not None # for mypy

    request_dict: dict[str, Any] = {
        'status': TaskExecution.Status.RUNNING.name,
        'task': {
            'name': 'Auto Unknown Method Task',
            'run_environment': {
                'name': api_key_run_environment.name,
            },
            'execution_method_capability': {
                'type': 'Unknown',
            }
        }
    }

    if was_auto_created is not None:
        request_dict['task']['was_auto_created'] = was_auto_created

    if passive is not None:
        request_dict['task']['passive'] = passive

    response = client.post(url, request_dict)

    assert response.status_code == status_code
    response_dict = cast(dict[str, Any], response.data)

    if status_code == 201:
        task_execution_uuid = response_dict['uuid']

        task_execution = TaskExecution.objects.get(uuid=task_execution_uuid)

        ensure_serialized_task_execution_valid(
                response_task_execution=response_dict,
                task_execution=task_execution, user=user,
                group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                api_key_run_environment=api_key_run_environment)

        task_dict = response_dict['task']
        task_uuid = task_dict['uuid']

        task = Task.objects.get(uuid=task_uuid)

        assert task_dict['name'] == task.name
        assert task.name == 'Auto Unknown Method Task'
        assert task.was_auto_created == was_auto_created
        assert task.passive == passive
        assert task.execution_method_type == UnknownExecutionMethod.NAME
        assert task.execution_method().name == UnknownExecutionMethod.NAME
    else:
        check_validation_error(response, validation_error_attribute,
                error_code)


@pytest.mark.django_db
@pytest.mark.parametrize("""
    status,
    status_code, validation_error_attribute, error_code,
""", [
    (TaskExecution.Status.MANUALLY_STARTED.name,
     400, 'status', 'invalid'),
    (TaskExecution.Status.RUNNING.name,
     201, None, None),
    (TaskExecution.Status.SUCCEEDED.name,
     201, None, None),
    (TaskExecution.Status.FAILED.name,
     201, None, None),
])
def test_task_execution_of_passive_task_creation(
        status,
        status_code, validation_error_attribute, error_code,
        user_factory, group_factory, run_environment_factory,
        unknown_execution_method_task_factory, task_execution_factory,
        api_client) -> None:
    """
    Test creation of Task Executions associated with passive Tasks
    """

    user = user_factory()

    _task_execution, _task, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_scope_type=SCOPE_TYPE_CORRECT,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=unknown_execution_method_task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    assert api_key_run_environment is not None # for mypy

    task = unknown_execution_method_task_factory(
            run_environment=api_key_run_environment,
            created_by_group=api_key_run_environment.created_by_group,
            passive=True)

    request_dict = {
        'status': status,
        'task': {
            'uuid': str(task.uuid),
        }
    }

    response = client.post(url, request_dict)

    assert response.status_code == status_code
    response_dict = cast(dict[str, Any], response.data)

    if status_code == 201:
        task_execution_uuid = response_dict['uuid']

        task_execution = TaskExecution.objects.get(uuid=task_execution_uuid)

        ensure_serialized_task_execution_valid(
                response_task_execution=response_dict,
                task_execution=task_execution, user=user,
                group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                api_key_run_environment=api_key_run_environment)
    else:
        check_validation_error(response, validation_error_attribute,
                error_code)


@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_create_history_purging(subscription_plan,
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory,
        api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    task_execution, task, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_scope_type=SCOPE_TYPE_CORRECT,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    assert task_execution is None

    request_data = make_request_body(uuid_send_type=SEND_ID_NONE,
            task_send_type=SEND_ID_CORRECT,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=None,
            task_execution=None,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            task=task)

    assert TaskExecution.objects.count() == 0

    utc_now = timezone.now()
    completed_task_execution_ids: List[int] = []
    for i in range(3):
        te = task_execution_factory(task=task,
                status=random.choice(TaskExecution.COMPLETED_STATUSES),
                finished_at = utc_now - timedelta(minutes=i))
        te.save()
        completed_task_execution_ids.append(te.id)

    utc_now = timezone.now()

    subscription = Subscription(group=group,
          subscription_plan=subscription_plan, active=True,
          start_at=utc_now - timedelta(minutes=1))
    subscription.save()

    plan = subscription.subscription_plan
    assert plan is not None
    plan.max_task_execution_history_items = 3
    plan.save()

    response = client.post(url, data=request_data)

    assert response.status_code == 201
    assert TaskExecution.objects.count() == 3

    for i in range(3):
        id = completed_task_execution_ids[i]
        exists = (TaskExecution.objects.filter(id=id).count() == 1)
        if i < 2:
            assert exists
        else:
            assert not exists


@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_create_with_legacy_task_property(
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory,
        api_client) -> None:
    """
    Tests that the 'process_type' property sent by legacy clients is still
    accepted.
    """

    user = user_factory()

    task_execution, _task, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK,
            api_key_scope_type=SCOPE_TYPE_CORRECT,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    request_data = make_request_body(uuid_send_type=SEND_ID_NONE,
            task_send_type=SEND_ID_CORRECT,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            task_execution=task_execution,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            task_property_name='process_type')

    old_count = TaskExecution.objects.count()

    response = client.post(url, data=request_data)

    assert response.status_code == 201

    new_count = TaskExecution.objects.count()
    assert new_count == old_count + 1

    response_task_execution = cast(dict[str, Any], response.data)
    task_execution_uuid = response_task_execution['uuid']
    created_task_execution = TaskExecution.objects.get(uuid=task_execution_uuid)

    ensure_serialized_task_execution_valid(response_task_execution=response_task_execution,
            task_execution=created_task_execution, user=user,
            group_access_level= UserGroupAccessLevel.ACCESS_LEVEL_TASK,
            api_key_access_level= UserGroupAccessLevel.ACCESS_LEVEL_TASK,
            api_key_run_environment=api_key_run_environment)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  request_uuid_send_type, body_uuid_send_type,
  task_send_type,
  status_code, validation_error_attribute, error_code
""", [
  # Admin with unscoped API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Developer with unscoped API Key succeeds when UUID in body matches
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   SEND_ID_CORRECT,
   200, None, None),

  # Developer with unscoped API Key fails with 422 when UUID in body does not match
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, SEND_ID_WRONG,
   None,
   422, 'uuid', 'invalid'),

  # Developer with unscoped API Key fails with 400 when Task is
  # specifically empty
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   SEND_ID_NONE,
   400, 'task', 'null'),

  # Developer with unscoped API Key cannot attach a Task in the
  # wrong Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   SEND_ID_IN_WRONG_GROUP,
   422, 'task', 'not_found'),

  # Task with properly scoped API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Support with properly scoped API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Observer with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   None,
   403, None, None),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   None,
   403, None, None),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Support user with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Observer with JWT token fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   None,
   403, None, None),

  # Task with API key scoped to correct Run Environment,
  # same Run Environment in request succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   200, None, None),

  # Task with API key scoped to correct Run Environment,
  # omits Task in body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Developer with developer API key scoped to a Run Environment gets 400
  # when specifying a different Task
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_OTHER,
   422, 'task', 'invalid'),

  # Developer with developer API key scoped to a Run Environment gets 404
  # when updating a Task Execution which has a Task scoped to a different
  # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   404, None, None),

  # Task with API key scoped to a Run Environment gets
  # validation error when specifying a Task in another Run Environment to
  # replace the existing Task
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'task', 'not_found'),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_NONE,
   SEND_ID_NOT_FOUND, None,
   None,
   404, None, None),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_NONE,
   SEND_ID_IN_WRONG_GROUP, None,
   None,
   404, None, None),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, None,
   None,
   401, None, None),
])
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_update_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        request_uuid_send_type: str, body_uuid_send_type: Optional[str],
        task_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        error_code: Optional[str],
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory,
        api_client) -> None:
    """
    This only tests access control to the PATCH endpoint, not the actual changes.
    """

    user = user_factory()

    task_execution, _task, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=request_uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    request_data = make_request_body(uuid_send_type=body_uuid_send_type,
            task_send_type=task_send_type,
            user=user,
            api_key_run_environment=api_key_run_environment,
            task_execution=task_execution,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory)

    old_count = TaskExecution.objects.count()

    response = client.patch(url, request_data)

    assert response.status_code == status_code
    assert TaskExecution.objects.count() == old_count

    task_execution.refresh_from_db()

    if status_code == 200:
        assert group_access_level is not None

        ensure_serialized_task_execution_valid(
                response_task_execution=cast(dict[str, Any], response.data),
                task_execution=task_execution, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)
    else:
        check_validation_error(response, validation_error_attribute,
                error_code)

@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_update_conflict(
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory,
        api_client) -> None:
    """
    Test status code if response Task Execution status does not match request.
    """

    task_execution, _task, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK,
            api_key_scope_type=SCOPE_TYPE_NONE,
            uuid_send_type=SEND_ID_CORRECT,
            user=user_factory(),
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    task_execution.status = TaskExecution.Status.STOPPING
    task_execution.save()

    response = client.patch(url, {
      'status': TaskExecution.Status.RUNNING.name
    })

    assert response.status_code == 409
    response_dict = cast(dict[str, Any], response.data)
    assert response_dict['status'] == TaskExecution.Status.STOPPED.name


@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_update_unmodifiable_properties(
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory,
        api_client) -> None:

    user = user_factory()

    task_execution, _task, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK,
            api_key_scope_type=SCOPE_TYPE_NONE,
            uuid_send_type=SEND_ID_CORRECT,
            user=user_factory(),
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    finished_at = timezone.now()
    started_at = timezone.now() - timedelta(seconds=120)
    task_execution.started_at = started_at
    task_execution.started_by = user
    task_execution.finished_at = finished_at
    task_execution.kill_started_at = finished_at
    task_execution.kill_finished_at = finished_at
    task_execution.killed_by = user
    task_execution.marked_done_at = finished_at
    task_execution.marked_done_by = user
    task_execution.status = TaskExecution.Status.STOPPING
    task_execution.save()

    user_2 = user_factory()

    response = client.patch(url, {
      'status': TaskExecution.Status.STOPPED.name,
      'started_at': '2020-09-01T00:00:00Z',
      'started_by': user_2.username,
      'finished_at': '2020-09-01T00:20:00Z',
      'killed_by': user_2.username,
      'kill_started_at': '2020-09-01T00:10:00Z',
      'kill_finished_at': '2020-09-01T00:15:00Z',
      'marked_done_by': user_2.username,
      'marked_done_at': '2020-09-01T00:09:00Z',
    })

    assert response.status_code == 200
    response_dict = cast(dict[str, Any], response.data)
    assert response_dict['status'] == TaskExecution.Status.STOPPED.name
    assert response_dict['started_by'] == user.username
    assert response_dict['started_at'] == iso8601_with_z(started_at)
    assert response_dict['finished_at'] == iso8601_with_z(finished_at)
    assert response_dict['killed_by'] == user.username
    assert response_dict['kill_started_at'] == iso8601_with_z(finished_at)
    assert response_dict['kill_finished_at'] == iso8601_with_z(finished_at)
    assert response_dict['marked_done_by'] == user.username
    assert response_dict['marked_done_at'] == iso8601_with_z(finished_at)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  uuid_send_type,
  status_code
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_CORRECT,
   204),

  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT,
   204),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT,
   403),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT,
   403),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT,
   204),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT,
   204),

  # Observer with JWT token failes with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT,
   403),

  # Developer with developer API key scoped to correct Run Environment, explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT,
   204),

  # Developer with developer API key scoped to different Run Environment gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT,
   404),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND,
   404),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_IN_WRONG_GROUP,
   404),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT,
   401),
])
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_delete(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory, api_client) -> None:
    user = user_factory()

    task_execution, _task, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            task_execution_factory=task_execution_factory,
            api_client=api_client)

    response = client.delete(url)

    assert response.status_code == status_code

    exists = TaskExecution.objects.filter(pk=task_execution.pk).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists
