from typing import Any, Dict, List, Optional, Tuple, cast

from datetime import timedelta
import uuid
from urllib.parse import quote

from django.utils import timezone

from django.contrib.auth.models import User

from processes.models import (
  UserGroupAccessLevel, Subscription,
  RunEnvironment, Workflow
)

from processes.serializers import (
    WorkflowSummarySerializer, WorkflowSerializer
)

import pytest

from rest_framework.test import APIClient

from moto import mock_ecs, mock_sts, mock_events

from conftest import *


def ensure_serialized_workflow_valid(response_workflow: Dict[str, Any],
        workflow: Workflow, user: User,
        group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None,
        summary_only: bool = False) -> None:
    context = context_with_authenticated_request(user=user,
            group=workflow.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    if summary_only:
        assert response_workflow== WorkflowSummarySerializer(workflow,
                context=context).data
    else:
        assert response_workflow== WorkflowSerializer(workflow,
                context=context).data

    if workflow.run_environment:
        assert response_workflow['run_environment']['uuid'] == str(workflow.run_environment.uuid)
    else:
        assert response_workflow['run_environment'] is None

    if api_key_run_environment:
        assert workflow.run_environment is not None
        assert api_key_run_environment.pk == workflow.run_environment.pk

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
   200, [0, 1, 2]),

  # Admin with Admin API key, no explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_NONE,
   200, [0, 1, 2]),

  # Observer with JWT token, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   False, SEND_ID_CORRECT,
   200, [0, 1, 2]),

  # Observer in single group with JWT token, no explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   False, SEND_ID_NONE,
   200, [0, 1, 2]),

  # Admin in multiple groups with JWT token, no explicit group yields 400
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   True, SEND_ID_NONE,
   400, None),

  # Developer in multiple groups with JWT token, explicit group yields 200
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   True, SEND_ID_CORRECT,
   200, [0, 1, 2]),

  # Admin with Observer API key, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   False, SEND_ID_CORRECT,
   200, [0, 1, 2]),

  # Admin with multiple groups with Observer API key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   True, SEND_ID_CORRECT,
   200, [0, 1, 2]),

  # No API key with no explicit group in request yields 400
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   True, SEND_ID_NONE,
   400, None),

  # API key with no explicit group in request succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   True, SEND_ID_NONE,
   200, [0, 1, 2]),

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
def test_workflow_list(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        user_has_another_group: bool, send_group_id_type: str,
        status_code: int, expected_indices: List[int],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    another_group = group_factory()

    if user_has_another_group:
        set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    workflow_group = group

    production_run_environment = run_environment_factory(created_by_group=group)
    test_run_environment = run_environment_factory(created_by_group=group)

    workflows = [
      workflow_factory(name='Production', created_by_group=workflow_group,
              run_environment=production_run_environment),
      workflow_factory(name='Scopeless', created_by_group=workflow_group,
              run_environment=None),
      workflow_factory(name='Test', created_by_group=workflow_group,
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

    response = client.get('/api/v1/workflows/', params)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        page = response.data
        assert page['count'] == len(expected_indices)
        results = page['results']

        for i in expected_indices:
            response_workflow = results[i]
            target_workflow = workflows[expected_indices[i]]
            ensure_serialized_workflow_valid(response_workflow,
                    workflow=target_workflow, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment,
                    summary_only=True)


def common_setup(is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str, existing_has_run_environment: bool,
        user, group_factory, run_environment_factory, workflow_factory,
        api_client, existing_api_key_run_environment: Optional[RunEnvironment] = None) \
        -> Tuple[Workflow, Optional[RunEnvironment], APIClient, str]:
    group = user.groups.first()

    if group_access_level is not None:
        set_group_access_level(user=user, group=group,
                access_level=group_access_level)

    workflow_group = group

    run_environment = run_environment_factory(created_by_group=workflow_group)
    another_run_environment = run_environment_factory(created_by_group=workflow_group)

    workflow_run_environment = run_environment if existing_has_run_environment else None

    workflow = workflow_factory(created_by_group=workflow_group,
      run_environment=workflow_run_environment)

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = existing_api_key_run_environment or run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = another_run_environment

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    url = '/api/v1/workflows/'

    if uuid_send_type != SEND_ID_NONE:
        workflow_uuid = uuid.uuid4()
        if uuid_send_type == SEND_ID_CORRECT:
            workflow_uuid = workflow.uuid
        elif uuid_send_type == SEND_ID_IN_WRONG_GROUP:
            another_group = group_factory()
            set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
            workflow_in_other_group = workflow_factory(
                    created_by_group=another_group)
            workflow_uuid = workflow_in_other_group.uuid

        url += quote(str(workflow_uuid)) + '/'

    return (workflow, api_key_run_environment, client, url)

def make_request_body(uuid_send_type: Optional[str],
        run_environment_send_type: Optional[str],
        user: User,
        api_key_run_environment: Optional[RunEnvironment],
        workflow: Workflow,
        group_factory, run_environment_factory,
        workflow_factory) -> Tuple[Dict[str, Any], Optional[RunEnvironment]]:
    request_data: Dict[str, Any] = {
      'name': 'Some Workflow',
    }

    if uuid_send_type == SEND_ID_NOT_FOUND:
        request_data['uuid'] = str(uuid.uuid4())
    elif uuid_send_type == SEND_ID_CORRECT:
        request_data['uuid'] = str(workflow.uuid)
    elif uuid_send_type == SEND_ID_WRONG:
        another_workflow = workflow_factory(created_by_group=workflow.created_by_group,
                run_environment=workflow.run_environment)
        request_data['uuid'] = str(another_workflow.uuid)

    run_environment: Optional[RunEnvironment] = None
    if run_environment_send_type is None:
        run_environment = workflow.run_environment
    else:
        if run_environment_send_type == SEND_ID_CORRECT:
            if api_key_run_environment:
                run_environment = api_key_run_environment
            elif workflow and workflow.run_environment:
                run_environment = workflow.run_environment
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
  uuid_send_type, existing_has_run_environment,
  status_code
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, True,
   200),

  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, True,
   200),

  # Developer with API Key succeeds with unscoped Profile
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, False,
   200),

  # Developer with API Key succeeds with unscoped Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, True,
   200),

  # Observer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, True,
   200),

  # Admin with API Key with support access succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, True,
   200),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, True,
   200),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, True,
   200),

  # Observer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   SEND_ID_CORRECT, True,
   200),

  # Developer with developer API key scoped to correct Run Environment,
  # explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, True,
   200),

  # Developer with developer API key scoped to different Run Environment gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, True,
   404),

  # Developer with developer API key scoped to Run Environment,
  # fetching Profile without Run Environment gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, False,
   404),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_NONE,
   SEND_ID_NOT_FOUND, True,
   404),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, SCOPE_TYPE_NONE,
   SEND_ID_IN_WRONG_GROUP, True,
   404),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, True,
   401),
])
def test_workflow_fetch(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        api_key_scope_type: str,
        uuid_send_type: str, existing_has_run_environment: bool,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        workflow_factory, api_client) -> None:
    user = user_factory()
    workflow, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            existing_has_run_environment=existing_has_run_environment,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            api_client=api_client)

    response = client.get(url)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        ensure_serialized_workflow_valid(response_workflow=response.data,
          workflow=workflow, user=user,
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

  # Developer with unscoped API Key succeeds when Run Environment is
  # specifically empty
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_NONE, SEND_ID_NONE,
   201, None),

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

  # uuid of existing workflow is present in request body
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

   # Developer with scoped API Key cannot update workflow with no
   # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_NONE,
   403, None),

   # Developer with scoped API Key cannot create workflow with a different
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
def test_workflow_create_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        body_uuid_type: str, run_environment_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, api_client) -> None:
    """
    This only tests access control to the CREATE endpoint, not the actual changes.
    """

    user = user_factory()

    workflow, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=SEND_ID_NONE,
            existing_has_run_environment=False,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            api_client=api_client)

    request_data, run_environment = make_request_body(
            uuid_send_type=body_uuid_type,
            run_environment_send_type=run_environment_send_type,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            workflow=workflow,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory)

    old_count = Workflow.objects.count()

    response = client.post(url, data=request_data)

    assert response.status_code == status_code

    new_count = Workflow.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1

        response_workflow = cast(Dict[str, Any], response.data)
        workflow_uuid = response_workflow['uuid']
        created_workflow = Workflow.objects.get(uuid=workflow_uuid)

        assert group_access_level is not None
        ensure_serialized_workflow_valid(response_workflow=response_workflow,
                workflow=created_workflow, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)
    else:
        assert new_count == old_count
        check_validation_error(response, validation_error_attribute)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  max_workflows, status_code
""", [
  (4, 201),
  (3, 422)
])
@mock_ecs
@mock_sts
@mock_events
def test_task_create_workflow_limit(max_workflows: int,
        status_code: int,
        subscription_plan, user_factory, group_factory,
        run_environment_factory, workflow_factory,
        api_client) -> None:
    """
    Test limits on the number of Workflows allowed per Group.
    """

    user = user_factory()
    group = user.groups.first()

    workflow, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_scope_type=SCOPE_TYPE_CORRECT,
            uuid_send_type=SEND_ID_NONE,
            existing_has_run_environment=False,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            api_client=api_client)

    request_data, run_environment = make_request_body(
            uuid_send_type=SEND_ID_NONE,
            run_environment_send_type=SEND_ID_CORRECT,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            workflow=workflow,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory)

    # Remove extra Workflow which messes up limit calculations
    workflow.delete()

    utc_now = timezone.now()
    for i in range(3):
        workflow = workflow_factory(created_by_group=group)
        workflow.save()

    utc_now = timezone.now()

    subscription_plan.max_workflows = max_workflows
    subscription_plan.save()

    subscription = Subscription(group=group,
          subscription_plan=subscription_plan, active=True,
          start_at=utc_now - timedelta(minutes=5))
    subscription.save()

    old_count = Workflow.objects.count()

    response = client.post(url, data=request_data)

    assert response.status_code == status_code

    new_count = Workflow.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1
    else:
        assert new_count == old_count
        response_dict = cast(Dict[str, Any], response.data)
        assert response_dict['error_code'] == 'limit_exceeded'




@pytest.mark.django_db
@pytest.mark.parametrize("""
  api_key_access_level, api_key_scope_type,
  run_environment_send_type, alert_method_send_type,
  existing_has_run_environment,
  status_code, validation_error_attribute
""", [
  # Developer authenticated with JWT succeeds with scoped Run Environment
  # where Alert Method is also scoped
  (None, None,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   False,
   201, None),

  # Developer authenticated with JWT succeeds with no Run Environment
  # where Alert Method is also unscoped
  (None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   False,
   201, None),

  # Developer authenticated with JWT succeeds with no Run Environment
  # where Alert Method is scoped to another Run Environment.
  # Existing is unscoped.
  (None, None,
   SEND_ID_NONE, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   False,
   201, None),

  # Developer authenticated with JWT succeeds with a specific Run Environment
  # where Alert Method is scoped correctly
  (None, None,
   SEND_ID_OTHER, SEND_ID_CORRECT,
   True,
   201, None),
  # Developer authenticated with JWT gets 422 with a specific Run Environment
  # where Alert Method is scoped to a different run environment
  (None, None,
   SEND_ID_CORRECT, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   True,
   422, 'alert_methods'),

  # Developer authenticated with JWT gets 422 with a specific Run Environment
  # where Alert Method is unscoped
  (None, None,
   SEND_ID_OTHER, SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   True,
   201, None),

  # Developer with unscoped API Key succeeds
  # where Workflow and Alert Method are both unscoped
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   False,
   201, None),

  # Developer with unscoped API Key succeeds
  # where Workflow is scoped but Alert Method is unscoped
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   True,
   201, None),

  # Developer with unscoped API Key succeeds
  # where Run Environment is omitted and Alert Method is unscoped.
  # Existing is unscoped.
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   None, SEND_ID_CORRECT,
   False,
   201, None),

  # Developer with unscoped API Key succeeds
  # where Run Environment is omitted and Alert Method is unscoped.
  # Existing is scoped.
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   None, SEND_ID_CORRECT,
   True,
   201, None),

 # Developer with unscoped API Key succeeds when Alert Method Run Environment
 # matches Alert Method Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_OTHER, SEND_ID_OTHER,
   True,
   201, None),
 # Developer with unscoped API Key fails when Workflow Run Environment
 # does not match Alert Method Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_OTHER, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   True,
   422, 'alert_methods'),

  # Developer with scoped API Key succeeds with correct Run Environment
  # and an Alert Method that scoped to the same Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   True,
   201, None),

  # Developer with scoped API Key succeeds with no explicit Run Environment
  # and an Alert Method that scoped to the API Key's Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   None, SEND_ID_CORRECT,
   True,
   201, None),

  # Developer with scoped API Key fails using with Workflow Run Environment and
  # Alert Method with different Run Environment.
  # Existing Workflow is scoped.
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   True,
   422, 'alert_methods'),

  # Developer with scoped API Key fails using with no explicit Run Environment
  # Alert Method with different Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   None, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   True,
   422, 'alert_methods'),

  # Developer with scoped API Key fails using matching Run Environment
  # but unscoped Alert Method
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   True,
   201, None),

  # Developer with scoped API Key fails using no explicit Run Environment
  # but unscoped Alert Method
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   None, SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   True,
   201, None),
])
def test_workflow_set_alert_methods(
        api_key_access_level: Optional[int], api_key_scope_type: str,
        run_environment_send_type: Optional[str],
        alert_method_send_type: Optional[str],
        existing_has_run_environment: bool,
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, alert_method_factory,
        api_client) -> None:
    """
    Tests for setting Alert Methods.
    """
    group_access_level = UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER

    user = user_factory()

    for is_post in [True, False]:
        uuid_send_type = SEND_ID_NONE if is_post else SEND_ID_CORRECT

        workflow, api_key_run_environment, client, url = common_setup(
                is_authenticated=True,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_scope_type=api_key_scope_type,
                uuid_send_type=uuid_send_type,
                existing_has_run_environment=existing_has_run_environment,
                user=user,
                group_factory=group_factory,
                run_environment_factory=run_environment_factory,
                workflow_factory=workflow_factory,
                api_client=api_client)


        old_count = Workflow.objects.count()


        # Run Environment is required, so always send it for creation
        if is_post:
            run_environment_send_type = SEND_ID_CORRECT

        request_data, run_environment = make_request_body(
                uuid_send_type=None,
                run_environment_send_type=run_environment_send_type,
                user=user,
                group_factory=group_factory,
                api_key_run_environment=api_key_run_environment,
                workflow=workflow,
                run_environment_factory=run_environment_factory,
                workflow_factory=workflow_factory)

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
            request_data['name'] = 'Updated Workflow'
            response = client.patch(url, data=request_data)

        actual_status_code = status_code

        if status_code == 201 and not is_post:
            actual_status_code = 200

        assert response.status_code == actual_status_code

        new_count = Workflow.objects.count()

        if status_code == 201:
            if is_post:
                assert new_count == old_count + 1
            else:
                assert new_count == old_count

            response_workflow = cast(Dict[str, Any], response.data)
            workflow_uuid = response_workflow['uuid']
            created_workflow = Workflow.objects.get(uuid=workflow_uuid)

            assert group_access_level is not None
            ensure_serialized_workflow_valid(response_workflow=response_workflow,
                    workflow=created_workflow, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)

            assert(response_workflow['alert_methods'][0]['uuid'] == str(alert_method.uuid))
        else:
            assert new_count == old_count
            check_validation_error(response, validation_error_attribute)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  request_uuid_send_type, body_uuid_send_type,
  run_environment_send_type, existing_has_run_environment,
  status_code, validation_error_attribute,
""", [
  # Admin with unscoped API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_CORRECT, None,
   None, True,
   200, None),

  # Developer with unscoped API Key succeeds when UUID in body matches
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   SEND_ID_CORRECT, True,
   200, None),

  # Developer with unscoped API Key fails with 422 when UUID in body does not match
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_WRONG,
   SEND_ID_CORRECT, True,
   422, 'uuid'),

  # Developer with unscoped API Key succeeds when UUID in body is not found
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_WRONG,
   SEND_ID_NONE, True,
   422, 'uuid'),

  # Developer with unscoped API Key succeeds in unscoping Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_NONE, True,
   200, None),

  # Developer with unscoped API Key succeeds in updating unscoped Workflow
  # when Run Environment is not specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_NONE, False,
   200, None),

  # Developer with unscoped API Key succeeds when Run Environment is specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_OTHER, True,
   200, None),

  # Developer with API Key succeeds when Run Environment is not specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   None, True,
   200, None),

  # Developer with unscoped API Key cannot attach a Run Environment in the
  # wrong Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_IN_WRONG_GROUP, False,
   422, 'run_environment'),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, None,
   None, True,
   403, None),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, None,
   None, True,
   403, None),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, None,
   None, True,
   200, None),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, None,
   None, True,
   200, None),

  # Developer with JWT token succeeds in removing Run Environment scope
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, None,
   SEND_ID_NONE, False,
   200, None),

  # Support user with JWT token fails with 403 on scoped Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, None,
   None, True,
   403, None),

  # Support user with JWT token fails with 403 on unscoped Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, None,
   None, False,
   403, None),

  # Developer with developer API key scoped to correct Run Environment,
  # same Run Environment in request succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT, True,
   200, None),

  # Developer with developer API key scoped to correct Run Environment,
  # omits Run Environment in body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   None, True,
   200, None),

  # Developer with developer API key scoped to a Run Environment gets 400
  # when specifying a different Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_OTHER, True,
   422, 'run_environment'),

  # Developer with developer API key scoped to a Run Environment gets 403
  # when unscoping Worklow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_NONE, True,
   403, None),

  # Developer with developer API key scoped to a Run Environment gets 404
  # when specifying scoped Run Environment to replace blank Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_NONE, False,
   404, None),

  # Developer with developer API key scoped to a Run Environment gets 404
  # when specifying scoped Run Environment to replace other Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT, True,
   404, None),

  # Developer with developer API key scoped to a Run Environment gets
  # validation error when specifying another Run Environment to replace scoped
  # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_OTHER, True,
   422, 'run_environment'),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, None,
   None, True,
   404, None),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_IN_WRONG_GROUP, None,
   None, True,
   404, None),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, None,
   None, True,
   401, None),
])
@mock_ecs
@mock_sts
@mock_events
def test_workflow_update_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        request_uuid_send_type: str, body_uuid_send_type: Optional[str],
        run_environment_send_type: str, existing_has_run_environment: bool,
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, api_client) -> None:
    """
    This only tests access control to the PATCH endpoint, not the actual changes.
    """

    user = user_factory()

    workflow, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=request_uuid_send_type,
            existing_has_run_environment=existing_has_run_environment,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            api_client=api_client)

    request_data, run_environment = make_request_body(
            uuid_send_type=body_uuid_send_type,
            run_environment_send_type=run_environment_send_type,
            user=user,
            api_key_run_environment=api_key_run_environment,
            workflow=workflow,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory)

    old_count = Workflow.objects.count()

    response = client.patch(url, request_data)

    assert response.status_code == status_code
    assert Workflow.objects.count() == old_count

    workflow.refresh_from_db()

    if status_code == 200:
        assert group_access_level is not None

        ensure_serialized_workflow_valid(
          response_workflow=cast(Dict[str, Any], response.data),
          workflow=workflow, user=user,
          group_access_level=group_access_level,
          api_key_access_level=api_key_access_level,
          api_key_run_environment=api_key_run_environment)
    else:
        check_validation_error(response, validation_error_attribute)

@pytest.mark.django_db
@pytest.mark.parametrize("""
  api_key_access_level, api_key_scope_type,
  run_environment_send_type, wti_send_type,
  existing_has_run_environment,
  status_code, validation_error_attribute
""", [
  # Developer authenticated with JWT succeeds with scoped Run Environment
  # where Workflow Task Instance is also scoped
  (None, None,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   False,
   201, None),

  # Developer authenticated with JWT succeeds with no Run Environment
  (None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   False,
   201, None),

  # Developer authenticated with JWT succeeds with no Run Environment
  # where Task is scoped to another Run Environment.
  # Existing is unscoped.
  (None, None,
   SEND_ID_NONE, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   False,
   201, None),

  # Developer authenticated with JWT succeeds with no Run Environment
  # where Workflow Task Instance is also unscoped
  (None, None,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   True,
   201, None),

  # Developer authenticated with JWT succeeds with a specific Run Environment
  # where Workflow Task Instance is scoped correctly
  (None, None,
   SEND_ID_OTHER, SEND_ID_CORRECT,
   True,
   201, None),

  # Developer authenticated with JWT gets 422 with a specific Run Environment
  # where Workflow Task Instance is scoped to a different Run Environment
  (None, None,
   SEND_ID_CORRECT, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   True,
   422, 'workflow_task_instances'),

  # Developer with unscoped API Key succeeds
  # where Workflow is unscoped. Existing Workflow is unscoped.
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   False,
   201, None),

  # Developer with unscoped API Key succeed where Workflow is unscoped.
  # Existing Workflow is scoped.
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   True,
   201, None),

  # Developer with unscoped API Key succeeds
  # where Run Environment is omitted. Existing is unscoped.
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   None, SEND_ID_CORRECT,
   False,
   201, None),

  # Developer with unscoped API Key succeeds where Run Environment is omitted.
  # Existing is scoped.
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   None, SEND_ID_CORRECT,
   True,
   201, None),

 # Developer with unscoped API Key succeeds when Workflow Task Instance Run Environment
 # matches Workflow Task Instance Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_OTHER, SEND_ID_OTHER,
   True,
   201, None),

 # Developer with unscoped API Key fails when Workflow Task Instance Run Environment
 # does not match Workflow Task Instance Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_OTHER, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   True,
   422, 'workflow_task_instances'),

  # Developer with scoped API Key succeeds with correct Run Environment
  # and an Workflow Task Instance that scoped to the same Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   True,
   201, None),

  # Developer with scoped API Key succeeds with no explicit Run Environment
  # and an Workflow Task Instance that scoped to the API Key's Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   None, SEND_ID_CORRECT,
   True,
   201, None),

  # Developer with scoped API Key fails using with workflow Run Environment and
  # Workflow Task Instance with different Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   True,
   422, 'workflow_task_instances'),

  # Developer with scoped API Key fails using with no explicit Run Environment
  # Workflow Task Instance with different Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   None, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   True,
   422, 'workflow_task_instances'),
])
@mock_ecs
@mock_sts
@mock_events
def test_workflow_set_task_instances(
        api_key_access_level: Optional[int], api_key_scope_type: str,
        run_environment_send_type: Optional[str], wti_send_type: Optional[str],
        existing_has_run_environment: bool,
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, task_factory,
        api_client) -> None:
    """
    Tests for setting task instances.
    """
    group_access_level = UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER

    user = user_factory()

    reuse_last_workflow = False
    workflow_uuid: Optional[str] = None
    wti_uuid: Optional[str] = None
    previous_run_environment: Optional[RunEnvironment] = None

    for is_post in [True, False, False]:
        uuid_send_type = SEND_ID_NONE if is_post else SEND_ID_CORRECT

        existing_api_key_run_environment: Optional[RunEnvironment] = None

        if (not is_post) and reuse_last_workflow:
            existing_api_key_run_environment = previous_run_environment

        workflow, api_key_run_environment, client, url = common_setup(
                is_authenticated=True,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_scope_type=api_key_scope_type,
                uuid_send_type=uuid_send_type,
                existing_has_run_environment=existing_has_run_environment,
                user=user,
                group_factory=group_factory,
                run_environment_factory=run_environment_factory,
                workflow_factory=workflow_factory,
                api_client=api_client,
                existing_api_key_run_environment=existing_api_key_run_environment)

        old_count = Workflow.objects.count()

        request_data, run_environment = make_request_body(
                uuid_send_type=None,
                run_environment_send_type=run_environment_send_type,
                user=user,
                group_factory=group_factory,
                api_key_run_environment=api_key_run_environment,
                workflow=workflow,
                run_environment_factory=run_environment_factory,
                workflow_factory=workflow_factory)

        task_group = user.groups.first()

        if (not is_post) and reuse_last_workflow and previous_run_environment:
            run_environment = previous_run_environment

        task_run_environment = run_environment

        if wti_send_type == SEND_ID_CORRECT:
            task_run_environment = task_run_environment or \
                    api_key_run_environment or \
                    run_environment_factory(created_by_group=task_group)
        elif wti_send_type == SEND_ID_WRONG:
            task_group = group_factory()
        elif wti_send_type == SEND_ID_IN_WRONG_GROUP:
            task_group = group_factory()
            set_group_access_level(user=user, group=task_group,
                    access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
        elif wti_send_type == SEND_ID_WITH_OTHER_RUN_ENVIRONMENT:
            task_run_environment = run_environment_factory(created_by_group=task_group)

        task = task_factory(created_by_group=task_group,
                run_environment=task_run_environment)

        task_uuid = task.uuid
        if wti_send_type == SEND_ID_NOT_FOUND:
            task_uuid = uuid.uuid4()

        if (not is_post) and reuse_last_workflow and workflow_uuid and wti_uuid:
            del request_data['name']
            request_data.pop('run_environment', None)
            url = '/api/v1/workflows/' + quote(workflow_uuid) + '/'
            wti_body: Dict[str, Any] = {
                'uuid': wti_uuid
            }
        else:
            if not is_post:
                # Prevent conflict with previous iteration's created entity
                request_data['name'] = 'Updated Workflow'

            wti_body = {
                'uuid': 'NEW_1',
                'name': 'Step 1',
            }

        wti_body['task'] = {
            'uuid': str(task_uuid)
        }

        request_data['workflow_task_instances'] = [wti_body]

        if is_post:
            response = client.post(url, data=request_data)
        else:
            response = client.patch(url, data=request_data)

        actual_status_code = status_code

        if status_code == 201 and not is_post:
            actual_status_code = 200

        assert response.status_code == actual_status_code

        new_count = Workflow.objects.count()

        if status_code == 201:
            if is_post:
                assert new_count == old_count + 1
            else:
                assert new_count == old_count

            response_workflow = cast(Dict[str, Any], response.data)
            workflow_uuid = response_workflow['uuid']
            created_workflow = Workflow.objects.get(uuid=workflow_uuid)

            assert group_access_level is not None
            ensure_serialized_workflow_valid(response_workflow=response_workflow,
                    workflow=created_workflow, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)

            workflow_uuid = response_workflow['uuid']
            wti_uuid = response_workflow['workflow_task_instances'][0]['uuid']
            previous_run_environment = run_environment


            if not is_post:
                reuse_last_workflow = not reuse_last_workflow
            #print(f"{wti_uuid=}")


        else:
            assert new_count == old_count
            check_validation_error(response, validation_error_attribute)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  uuid_send_type, existing_has_run_environment,
  status_code
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_CORRECT, True,
   204),

  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, True,
   204),

  # Developer with unscoped API Key can deleted unscoped Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, False,
   204),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, True,
   403),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, True,
   403),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, True,
   204),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, True,
   204),

  # Developer with JWT token succeeds deleting unscoped Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, False,
   204),

  # Support user with JWT token failes with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, True,
   403),

  # Developer with developer API key scoped to Run Environment
  # cannot delete unscoped Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, False,
   404),

  # Developer with developer API key scoped to correct Run Environment, explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, True,
   204),

  # Developer with developer API key scoped to different Run Environment gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, True,
   404),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, True,
   404),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_IN_WRONG_GROUP, True,
   404),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, True,
   401),
])
@mock_ecs
@mock_sts
@mock_events
def test_workflow_delete(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str, existing_has_run_environment: bool,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        workflow_factory, api_client) -> None:
    user = user_factory()

    workflow, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            existing_has_run_environment=existing_has_run_environment,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            api_client=api_client)

    response = client.delete(url)

    assert response.status_code == status_code

    exists = Workflow.objects.filter(pk=workflow.pk).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists
