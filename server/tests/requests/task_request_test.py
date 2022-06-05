from typing import Any, List, Optional, Tuple, cast

from datetime import timedelta
import uuid
from urllib.parse import quote

from django.utils import timezone

from django.contrib.auth.models import User

from processes.execution_methods.unknown_execution_method import (
    UnknownExecutionMethod
)
from processes.models import (
  UserGroupAccessLevel, Subscription,
  Task, RunEnvironment
)


import pytest

from rest_framework.test import APIClient

from moto import mock_ecs, mock_sts, mock_events

from conftest import *


def ensure_serialized_task_valid(response_task: dict[str, Any],
        task: Task, user: User,
        group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> None:
    context = context_with_authenticated_request(user=user,
            group=task.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    validate_serialized_task(response_task, task, context=context)

    if api_key_run_environment:
        assert api_key_run_environment.pk == task.run_environment.pk

@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  user_has_another_group, send_group_id_type,
  status_code, expected_indices
""", [
  # Admin with Admin API key, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_CORRECT,
   200, [0, 1]),

  # Admin with Admin API key, no explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_NONE,
   200, [0, 1]),

  # Observer with JWT token, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   False, SEND_ID_CORRECT,
   200, [0, 1]),

  # Observer in single group with JWT token, no explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   False, SEND_ID_NONE,
   200, [0, 1]),

  # Admin in multiple groups with JWT token, no explicit group yields 400
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   True, SEND_ID_NONE,
   400, None),

  # Developer in multiple groups with JWT token, explicit group yields 200
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   True, SEND_ID_CORRECT,
   200, [0, 1]),

  # Admin with Observer API key, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   False, SEND_ID_CORRECT,
   200, [0, 1]),

  # Admin with multiple groups with Observer API key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   True, SEND_ID_CORRECT,
   200, [0, 1]),

  # No API key with no explicit group in request yields 400
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   True, SEND_ID_NONE,
   400, None),

  # API key with no explicit group in request succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   True, SEND_ID_NONE,
   200, [0, 1]),

  # Admin with Admin API key, explicit wrong group yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_WRONG,
   422, None),

  # Admin using JWT, explicit wrong group yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   False, SEND_ID_WRONG,
   422, None),

  # Admin using Admin API key, explicit bad group ID yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_NOT_FOUND,
   422, None),

  # Admin using JWT, explicit bad group ID yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   False, SEND_ID_NOT_FOUND,
   422, None),

  # Admin with Admin API key scoped to correct Run Environment, explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_CORRECT,
   False, SEND_ID_CORRECT,
   200, [0]),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   False, SEND_ID_CORRECT,
   401, None),

  # TODO: check filtering, non-default ordering
])
@mock_ecs
@mock_sts
@mock_events
def test_task_list(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        user_has_another_group: bool, send_group_id_type: str,
        status_code: int, expected_indices: List[int],
        user_factory, group_factory, run_environment_factory,
        task_factory, api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    another_group = group_factory()

    if user_has_another_group:
        set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    task_group = group

    production_run_environment = run_environment_factory(created_by_group=group)
    test_run_environment = run_environment_factory(created_by_group=group)

    tasks = [
      task_factory(name='Production', created_by_group=task_group,
              run_environment=production_run_environment),
      task_factory(name='Test', created_by_group=task_group,
              run_environment=test_run_environment)
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

    if send_group_id_type == SEND_ID_CORRECT:
        params['created_by_group__id'] = str(group.id)
    elif send_group_id_type == SEND_ID_NOT_FOUND:
        params['created_by_group__id'] = '666'
    elif send_group_id_type == SEND_ID_WRONG:
        params['created_by_group__id'] = str(another_group.id)

    response = client.get('/api/v1/tasks/', params)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        page = response.data
        assert page['count'] == len(expected_indices)
        results = page['results']

        for i in expected_indices:
            response_task = results[i]
            target_task = tasks[expected_indices[i]]
            ensure_serialized_task_valid(response_task,
                    task=target_task, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)


def common_setup(is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str,
        user, group_factory, run_environment_factory, task_factory, api_client) \
        -> Tuple[Task, Optional[RunEnvironment], APIClient, str]:
    group = user.groups.first()

    if group_access_level is not None:
        set_group_access_level(user=user, group=group,
                access_level=group_access_level)

    task_group = group

    run_environment = run_environment_factory(created_by_group=task_group)
    another_run_environment = run_environment_factory(created_by_group=task_group)

    task_run_environment = run_environment

    task = task_factory(created_by_group=task_group,
      run_environment=task_run_environment)

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = task_run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = another_run_environment

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    url = '/api/v1/tasks/'

    if uuid_send_type != SEND_ID_NONE:
        task_uuid = uuid.uuid4()
        if uuid_send_type == SEND_ID_CORRECT:
            task_uuid = task.uuid
        elif uuid_send_type == SEND_ID_IN_WRONG_GROUP:
            another_group = group_factory()
            set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
            task_in_other_group = task_factory(
                    created_by_group=another_group)
            task_uuid = task_in_other_group.uuid

        url += quote(str(task_uuid)) + '/'

    return (task, api_key_run_environment, client, url)

def make_request_body(uuid_send_type: Optional[str],
        run_environment_send_type: Optional[str],
        user: User,
        api_key_run_environment: Optional[RunEnvironment],
        task: Task,
        group_factory, run_environment_factory,
        task_factory) -> Tuple[dict[str, Any], Optional[RunEnvironment]]:
    request_data: dict[str, Any] = {
      'name': 'Some Task',
      'passive': False,
      'execution_method_capability': task.execution_method_capability
    }

    if uuid_send_type == SEND_ID_NOT_FOUND:
        request_data['uuid'] = str(uuid.uuid4())
    elif uuid_send_type == SEND_ID_CORRECT:
        request_data['uuid'] = str(task.uuid)
    elif uuid_send_type == SEND_ID_WRONG:
        another_task = task_factory(created_by_group=task.created_by_group,
                run_environment=task.run_environment)
        request_data['uuid'] = str(another_task.uuid)

    run_environment: Optional[RunEnvironment] = None
    if run_environment_send_type is None:
        run_environment = task.run_environment
    else:
        if run_environment_send_type == SEND_ID_CORRECT:
            if api_key_run_environment:
                run_environment = api_key_run_environment
            elif task and task.run_environment:
                run_environment = task.run_environment
        elif run_environment_send_type == SEND_ID_OTHER:
            run_environment = run_environment_factory(created_by_group=user.groups.first())
        elif run_environment_send_type == SEND_ID_IN_WRONG_GROUP:
            group = group_factory()
            set_group_access_level(user=user, group=group,
                    access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
            run_environment = run_environment_factory(created_by_group=group)
        elif run_environment_send_type == SEND_ID_NONE:
            request_data['run_environment'] = None

        if run_environment:
            request_data['run_environment'] = {
                'uuid': str(run_environment.uuid)
            }

    return (request_data, run_environment,)


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

  # Developer with API Key succeeds with unscoped Task
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
def test_task_fetch(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        task_factory, api_client) -> None:
    user = user_factory()
    task, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            api_client=api_client)

    response = client.get(url)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        ensure_serialized_task_valid(response_task=response.data,
          task=task, user=user,
          group_access_level=group_access_level,
          api_key_access_level=api_key_access_level,
          api_key_run_environment=api_key_run_environment)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  body_uuid_type, run_environment_send_type,
  status_code, validation_error_attribute
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None),

  # Developer with unscoped API Key fails with 400 when Run Environment is
  # specifically empty
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_NONE, SEND_ID_NONE,
   400, 'run_environment'),

  # Developer with unscoped API Key succeeds when Run Environment is specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None),

  # non-existent uuid is present in request body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, SEND_ID_CORRECT,
   400, 'uuid'),

  # uuid of existing Task is present in request body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_WRONG, SEND_ID_CORRECT,
   400, 'uuid'),

   # Developer with unscoped API Key cannot attach a Run Environment in the
   # wrong Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_NONE, SEND_ID_IN_WRONG_GROUP,
   422, 'run_environment'),

   # Developer with scoped API Key succeeds when Alert Method is scoped
   # with the same Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None),

   # Developer with scoped API Key succeeds when Run Environment is omitted
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, None,
   201, None),

   # Developer with scoped API Key cannot update Task with no
   # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_NONE,
   403, None),

   # Developer with scoped API Key cannot create Task with a different
   # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_OTHER,
   422, 'run_environment'),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   403, None),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   403, None),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None),

  # Support user with JWT token fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   403, None),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   401, None),
])
@mock_ecs
@mock_sts
@mock_events
def test_task_create_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        body_uuid_type: str, run_environment_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        task_factory, alert_method_factory,
        api_client) -> None:
    """
    This only tests access control to the CREATE endpoint, not the actual changes.
    """

    user = user_factory()

    task, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            api_client=api_client)

    request_data, run_environment = make_request_body(
            uuid_send_type=body_uuid_type,
            run_environment_send_type=run_environment_send_type,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            task=task,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory)

    old_count = Task.objects.count()

    response = client.post(url, data=request_data)

    assert response.status_code == status_code

    new_count = Task.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1

        response_task = cast(dict[str, Any], response.data)
        task_uuid = response_task['uuid']
        created_task = Task.objects.get(uuid=task_uuid)

        assert group_access_level is not None
        ensure_serialized_task_valid(response_task=response_task,
                task=created_task, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)
    else:
        assert new_count == old_count
        check_validation_error(response, validation_error_attribute)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  emc
""", [
  (None),
  ({}),
  ({ 'type': 'Unknown' }),
  ({ 'type': 'unknown' }),
  ({ 'type': 'UNKNOWN' }),
])
def test_task_create_passive_task(emc: dict[str, Any],
        user_factory, group_factory,
        run_environment_factory, task_factory,
        api_client) -> None:
    """
    Test execution method fallback to Unknown type.
    """

    user = user_factory()
    group = user.groups.first()

    task, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_scope_type=SCOPE_TYPE_CORRECT,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            api_client=api_client)

    request_data = {
      'name': 'Some Task',
      'passive': True,
      'execution_method_capability': emc
    }

    response = client.post(url, data=request_data)

    assert response.status_code == 201

    response_task = cast(dict[str, Any], response.data)
    task_uuid = response_task['uuid']
    created_task = Task.objects.get(uuid=task_uuid)

    assert created_task.execution_method_type == UnknownExecutionMethod.NAME
    assert created_task.passive

    ensure_serialized_task_valid(response_task=response_task,
            task=created_task, user=user,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=api_key_run_environment)



@pytest.mark.django_db
@pytest.mark.parametrize("""
  max_tasks, status_code
""", [
  (4, 201),
  (3, 422)
])
@mock_ecs
@mock_sts
@mock_events
def test_task_create_task_limit(max_tasks: int,
        status_code: int,
        subscription_plan, user_factory, group_factory,
        run_environment_factory, task_factory,
        api_client) -> None:
    """
    Test limits on the number of Tasks allowed per Group.
    """

    user = user_factory()
    group = user.groups.first()

    task, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_scope_type=SCOPE_TYPE_CORRECT,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            api_client=api_client)

    request_data, run_environment = make_request_body(
            uuid_send_type=SEND_ID_NONE,
            run_environment_send_type=SEND_ID_CORRECT,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            task=task,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory)

    # Remove extra Task which messes up limit calculations
    task.delete()

    utc_now = timezone.now()
    for i in range(3):
        task = task_factory(created_by_group=group)
        task.save()

    utc_now = timezone.now()

    subscription_plan.max_tasks = max_tasks
    subscription_plan.save()

    subscription = Subscription(group=group,
          subscription_plan=subscription_plan, active=True,
          start_at=utc_now - timedelta(minutes=5))
    subscription.save()

    old_count = Task.objects.count()

    response = client.post(url, data=request_data)

    assert response.status_code == status_code

    new_count = Task.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1

        response_task = cast(dict[str, Any], response.data)
        task_uuid = response_task['uuid']
        created_task = Task.objects.get(uuid=task_uuid)

        ensure_serialized_task_valid(response_task=response_task,
                task=created_task, user=user,
                group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                api_key_run_environment=api_key_run_environment)
    else:
        assert new_count == old_count
        response_dict = cast(dict[str, Any], response.data)
        assert response_dict['error_code'] == 'limit_exceeded'

@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_task_create_with_links(
        user_factory, group_factory, run_environment_factory,
        task_factory, api_client) -> None:
    user = user_factory()

    task, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_scope_type=SCOPE_TYPE_CORRECT,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            api_client=api_client)

    request_data, run_environment = make_request_body(
            uuid_send_type=SEND_ID_NONE,
            run_environment_send_type=SEND_ID_CORRECT,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            task=task,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory)

    request_data['links'] = [
        {
            'name': 'Cool Saas',
            'link_url_template': 'https://coolsaas.com/here',
            'icon_url': 'https://coolsaas.com/favicon.ico',
            'description': 'Cool link',
            'rank': 1,
        },
        {
            'name': 'Hot Saas',
            'link_url_template': 'https://hotsaas.com/here',
            'icon_url': 'https://hotsaas.com/favicon.ico',
            'description': 'Hot link',
            'rank': 2,
        },
    ]

    old_count = Task.objects.count()

    response = client.post(url, data=request_data)

    assert response.status_code == 201

    new_count = Task.objects.count()
    assert new_count == old_count + 1

    response_task = cast(dict[str, Any], response.data)
    task_uuid = response_task['uuid']
    created_task = Task.objects.get(uuid=task_uuid)

    ensure_serialized_task_valid(response_task=response_task,
            task=created_task, user=user,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=api_key_run_environment)


    links = created_task.tasklink_set.all()
    assert len(links) == 2
    link_0 = links[0]
    assert link_0.task.uuid == created_task.uuid
    assert link_0.name == 'Cool Saas'
    assert link_0.link_url_template == 'https://coolsaas.com/here'
    assert link_0.icon_url == 'https://coolsaas.com/favicon.ico'
    assert link_0.rank == 1

    link_1 = links[1]
    assert link_1.task.uuid == created_task.uuid
    assert link_1.name == 'Hot Saas'
    assert link_1.link_url_template == 'https://hotsaas.com/here'
    assert link_1.icon_url == 'https://hotsaas.com/favicon.ico'
    assert link_1.rank == 2

    body_links = response_task['links']

    for i in range(2):
        model_link = links[i]
        body_link = body_links[i]

        assert body_link['name'] == model_link.name
        assert body_link['icon_url'] == model_link.icon_url
        assert body_link['rank'] == model_link.rank

@pytest.mark.django_db
@pytest.mark.parametrize("""
  api_key_access_level, api_key_scope_type,
  run_environment_send_type, alert_method_send_type,
  status_code, validation_error_attribute
""", [
  # Developer authenticated with JWT succeeds with no Run Environment
  # where Alert Method is also unscoped
  (None, None,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   201, None),
  # Developer authenticated with JWT succeeds where Alert Method is scoped
  # correctly
  (None, None,
   SEND_ID_OTHER, SEND_ID_CORRECT,
   201, None),
  # Developer authenticated with JWT gets 422 where Alert Method is
  # scoped to a different Run Environment
  (None, None,
   SEND_ID_CORRECT, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'alert_methods'),
  # Developer authenticated with JWT gets succeeds a specific Run Environment
  # where Alert Method is unscoped
  (None, None,
   SEND_ID_OTHER, SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   201, None),
  # Developer with unscoped API Key succeeds
  # where Task and Alert Method are also unscoped
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   201, None),
  # Developer with unscoped API Key succeeds
  # where Run Environment is omitted and Alert Method is unscoped
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   None, SEND_ID_CORRECT,
   201, None),
 # Developer with unscoped API Key succeeds when Alert Method Run Environment
 # matches Alert Method Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_OTHER, SEND_ID_OTHER,
   201, None),
 # Developer with unscoped API Key fails when Alert Method Run Environment
 # does not match Alert Method Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_OTHER, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'alert_methods'),
  # Developer with scoped API Key succeeds with correct Run Environment
  # and an Alert Method that scoped to the same Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   201, None),
  # Developer with scoped API Key succeeds no explicit Run Environment
  # and an Alert Method that scoped to the API Key's Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   None, SEND_ID_CORRECT,
   201, None),
  # Developer with scoped API Key fails using with Task Run Environment and
  # Alert Method with different Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'alert_methods'),
  # Developer with scoped API Key fails using with no explicit Run Environment
  # Alert Method with different Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   None, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'alert_methods'),
  # Developer with scoped API Key succeeds using matching Run Environment
  # but unscoped Alert Method
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   201, None),
  # Developer with scoped API Key fails using no explicit Run Environment
  # but unscoped Alert Method
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   None, SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   201, None),
])
@mock_ecs
@mock_sts
@mock_events
def test_task_set_alert_methods(
        api_key_access_level: Optional[int], api_key_scope_type: str,
        run_environment_send_type: Optional[str],
        alert_method_send_type: Optional[str],
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        task_factory, alert_method_factory,
        api_client) -> None:
    """
    Tests for setting method details.
    """
    group_access_level = UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER

    user = user_factory()

    for is_post in [True, False]:
        uuid_send_type = SEND_ID_NONE if is_post else SEND_ID_CORRECT

        task, api_key_run_environment, client, url = common_setup(
                is_authenticated=True,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_scope_type=api_key_scope_type,
                uuid_send_type=uuid_send_type,
                user=user,
                group_factory=group_factory,
                run_environment_factory=run_environment_factory,
                task_factory=task_factory,
                api_client=api_client)

        old_count = Task.objects.count()

        # Run Environment is required, so always send it for creation
        if is_post:
            run_environment_send_type = SEND_ID_CORRECT

        request_data, run_environment = make_request_body(
                uuid_send_type=None,
                run_environment_send_type=run_environment_send_type,
                user=user,
                group_factory=group_factory,
                api_key_run_environment=api_key_run_environment,
                task=task,
                run_environment_factory=run_environment_factory,
                task_factory=task_factory)

        am_group = user.groups.first()
        am_run_environment = run_environment

        if alert_method_send_type == SEND_ID_CORRECT:
            am_run_environment = am_run_environment or \
                    api_key_run_environment
        if alert_method_send_type == SEND_ID_WRONG:
            am_group = group_factory()
        elif alert_method_send_type == SEND_ID_IN_WRONG_GROUP:
            am_group = group_factory()
            set_group_access_level(user=user, group=am_group,
                    access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
        elif alert_method_send_type == SEND_ID_WITH_OTHER_RUN_ENVIRONMENT:
            am_run_environment = run_environment_factory(created_by_group=am_group)
        elif alert_method_send_type == SEND_ID_WITHOUT_RUN_ENVIRONMENT:
            am_run_environment = None

        alert_method = alert_method_factory(created_by_group=am_group,
                run_environment=am_run_environment)

        if alert_method_send_type:
            am_uuid = alert_method.uuid
            if alert_method_send_type == SEND_ID_NOT_FOUND:
                am_uuid = uuid.uuid4()

            body_alert_methods = [{
                'uuid': str(am_uuid)
            }]

            request_data['alert_methods'] = body_alert_methods


        if is_post:
            response = client.post(url, data=request_data)
        else:
            # Prevent conflict with previous iteration's created entity
            request_data['name'] = 'Updated AM'
            response = client.patch(url, data=request_data)

        actual_status_code = status_code

        if status_code == 201 and not is_post:
            actual_status_code = 200

        assert response.status_code == actual_status_code

        new_count = Task.objects.count()

        if status_code == 201:
            if is_post:
                assert new_count == old_count + 1
            else:
                assert new_count == old_count

            response_task = cast(dict[str, Any], response.data)
            task_uuid = response_task['uuid']
            created_task = Task.objects.get(uuid=task_uuid)

            assert group_access_level is not None
            ensure_serialized_task_valid(response_task=response_task,
                    task=created_task, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)

            assert(response_task['alert_methods'][0]['uuid'] == str(alert_method.uuid))
        else:
            assert new_count == old_count
            check_validation_error(response, validation_error_attribute)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  request_uuid_send_type, body_uuid_send_type,
  run_environment_send_type,
  status_code, validation_error_attribute,
""", [
  # Admin with unscoped API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_CORRECT, None,
   None,
   200, None),

  # Developer with unscoped API Key succeeds when UUID in body matches
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   SEND_ID_CORRECT,
   200, None),

  # Developer with unscoped API Key fails with 422 when UUID in body does not match
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_WRONG,
   SEND_ID_CORRECT,
   422, 'uuid'),

  # Developer with unscoped API Key succeeds when UUID in body is not found
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_WRONG,
   SEND_ID_NONE,
   422, 'uuid'),

  # Developer with unscoped API Key fails with 422 when Run Environment is
  # specifically empty
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_NONE,
   400, 'run_environment'),

  # Developer with unscoped API Key succeeds when Run Environment is specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_OTHER,
   200, None),

  # Developer with API Key succeeds when Run Environment is not specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   None,
   200, None),

  # Developer with unscoped API Key cannot attach a Run Environment in the
  # wrong Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_IN_WRONG_GROUP,
   422, 'run_environment'),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, None,
   None,
   403, None),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, None,
   None,
   403, None),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, None,
   None,
   200, None),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, None,
   None,
   200, None),

  # Support user with JWT token failes with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, None,
   None,
   403, None),

  # Developer with developer API key scoped to correct Run Environment,
  # same Run Environment in request succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   200, None),

  # Developer with developer API key scoped to correct Run Environment,
  # sends same Run Environment in body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   200, None),

  # Developer with developer API key scoped to correct Run Environment,
  # omits Run Environment in body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   None,
   200, None),

  # Developer with developer API key scoped to a Run Environment gets 400
  # when specifying a different Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_OTHER,
   422, 'run_environment'),

  # Developer with developer API key scoped to a Run Environment gets 404
  # when specifying scoped Run Environment to replace other Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   404, None),

  # Developer with developer API key scoped to a Run Environment gets
  # validation error when specifying another Run Environment to replace scoped
  # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_OTHER,
   422, 'run_environment'),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, None,
   None,
   404, None),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_IN_WRONG_GROUP, None,
   None,
   404, None),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, None,
   None,
   401, None),
])
@mock_ecs
@mock_sts
@mock_events
def test_task_update_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        request_uuid_send_type: str, body_uuid_send_type: Optional[str],
        run_environment_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        alert_method_factory, task_factory,
        api_client) -> None:
    """
    This only tests access control to the PATCH endpoint, not the actual changes.
    """

    user = user_factory()

    task, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=request_uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            api_client=api_client)

    request_data, run_environment = make_request_body(
            uuid_send_type=body_uuid_send_type,
            run_environment_send_type=run_environment_send_type,
            user=user,
            api_key_run_environment=api_key_run_environment,
            task=task,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory)

    old_count = Task.objects.count()

    response = client.patch(url, request_data)

    assert response.status_code == status_code
    assert Task.objects.count() == old_count

    task.refresh_from_db()

    if status_code == 200:
        assert group_access_level is not None

        ensure_serialized_task_valid(
                response_task=cast(dict[str, Any], response.data),
                task=task, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)
    else:
        check_validation_error(response, validation_error_attribute)

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
def test_task_delete(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        task_factory, api_client) -> None:
    user = user_factory()

    task, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            task_factory=task_factory,
            api_client=api_client)

    response = client.delete(url)

    assert response.status_code == status_code

    exists = Task.objects.filter(pk=task.pk).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists
