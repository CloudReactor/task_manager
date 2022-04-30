from typing import Any, Dict, List, Optional, Tuple

from datetime import timedelta
import random
import uuid
from urllib.parse import quote

from django.utils import timezone

from django.contrib.auth.models import User

from processes.models import (
  Subscription, UserGroupAccessLevel, RunEnvironment,
  WorkflowExecution, Workflow,
)

import pytest

from rest_framework.test import APIClient

from moto import mock_ecs, mock_sts, mock_events

from conftest import *


def ensure_serialized_workflow_execution_valid(response_workflow_execution: Dict[str, Any],
        workflow_execution: WorkflowExecution, user: User,
        group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None,
        is_list: bool = False) -> None:
    context = context_with_authenticated_request(user=user,
            group=workflow_execution.workflow.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    if is_list:
        validate_serialized_workflow_execution_summary(
                response_workflow_execution, workflow_execution,
                context=context)
    else:
        validate_serialized_workflow_execution(response_workflow_execution,
                workflow_execution, context=context)

    if api_key_run_environment:
        assert workflow_execution.workflow.run_environment is not None
        assert api_key_run_environment.pk == workflow_execution.workflow.run_environment.pk

@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  user_has_another_group, send_group_id_type, send_workflow_uuid_type,
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

  # Support user in multiple groups with JWT token, explicit Workflow yields 200
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
def test_workflow_execution_list(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        user_has_another_group: bool, send_group_id_type: str,
        send_workflow_uuid_type: str,
        status_code: int, expected_indices: List[int],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, workflow_execution_factory, api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    another_group = group_factory()

    if user_has_another_group:
        set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    workflow_group = group

    production_run_environment = run_environment_factory(created_by_group=workflow_group)
    production_workflow = workflow_factory(created_by_group=workflow_group,
        run_environment=production_run_environment)

    test_run_environment = run_environment_factory(created_by_group=workflow_group)
    test_workflow = workflow_factory(created_by_group=workflow_group,
        run_environment=test_run_environment)

    workflow_executions = [
      workflow_execution_factory(workflow=production_workflow),
      workflow_execution_factory(workflow=test_workflow)
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
        params['workflow__created_by_group__id'] = group_id

    workflow_uuid: Optional[str] = None


    if send_workflow_uuid_type == SEND_ID_CORRECT:
        workflow_uuid = str(production_workflow.uuid)
    elif send_workflow_uuid_type == SEND_ID_NOT_FOUND:
        workflow_uuid = 'abc'

    if workflow_uuid:
        params['workflow__uuid'] = workflow_uuid

    response = client.get('/api/v1/workflow_executions/', params)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        page = response.data
        assert page['count'] == len(expected_indices)
        results = page['results']

        for i in expected_indices:
            response_workflow_execution = results[i]
            target_workflow_execution = workflow_executions[expected_indices[i]]
            ensure_serialized_workflow_execution_valid(response_workflow_execution,
                    workflow_execution=target_workflow_execution, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment,
                    is_list=True)


def common_setup(is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str,
        user, group_factory, run_environment_factory,
        workflow_factory, workflow_execution_factory, api_client) \
        -> Tuple[WorkflowExecution, Optional[RunEnvironment], APIClient, str]:
    group = user.groups.first()

    if group_access_level is not None:
        set_group_access_level(user=user, group=group,
                access_level=group_access_level)

    workflow_execution_group = group

    run_environment = run_environment_factory(created_by_group=workflow_execution_group)
    another_run_environment = run_environment_factory(created_by_group=workflow_execution_group)

    workflow = workflow_factory(created_by_group=group, run_environment=run_environment)

    workflow_execution_run_environment = run_environment
    workflow_execution = workflow_execution_factory(workflow=workflow)

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = workflow_execution_run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = another_run_environment

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    url = '/api/v1/workflow_executions/'

    if uuid_send_type != SEND_ID_NONE:
        workflow_execution_uuid = uuid.uuid4()
        if uuid_send_type == SEND_ID_CORRECT:
            workflow_execution_uuid = workflow_execution.uuid
        elif uuid_send_type == SEND_ID_IN_WRONG_GROUP:
            another_group = group_factory()
            set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
            workflow_in_other_group = workflow_factory(created_by_group=another_group)
            workflow_execution_in_other_group = workflow_execution_factory(
                    workflow=workflow_in_other_group)
            workflow_execution_uuid = workflow_execution_in_other_group.uuid

        url += quote(str(workflow_execution_uuid)) + '/'

    return (workflow_execution, api_key_run_environment, client, url)

def make_request_body(uuid_send_type: Optional[str],
        workflow_send_type: Optional[str],
        user: User,
        api_key_run_environment: Optional[RunEnvironment],
        workflow_execution: WorkflowExecution,
        group_factory, run_environment_factory, workflow_factory,
        workflow_execution_factory) -> Dict[str, Any]:
    request_data: Dict[str, Any] = {
      'status': 'RUNNING'
    }

    if uuid_send_type == SEND_ID_NOT_FOUND:
        request_data['uuid'] = str(uuid.uuid4())
    elif uuid_send_type == SEND_ID_CORRECT:
        request_data['uuid'] = str(workflow_execution.uuid)
    elif uuid_send_type == SEND_ID_WRONG:
        another_workflow_execution = workflow_execution_factory(
                workflow=workflow_execution.workflow)
        request_data['uuid'] = str(another_workflow_execution.uuid)

    run_environment: Optional[RunEnvironment] = None
    if workflow_send_type is None:
        run_environment = workflow_execution.workflow.run_environment
    else:
        workflow: Optional[Workflow] = None
        if workflow_send_type == SEND_ID_NONE:
            request_data['workflow'] = None
        else:
            if workflow_send_type == SEND_ID_CORRECT:
                if api_key_run_environment:
                    run_environment = api_key_run_environment
                else:
                    run_environment = workflow_execution.workflow.run_environment

                workflow = workflow_execution.workflow
            elif workflow_send_type == SEND_ID_OTHER:
                run_environment = workflow_execution.workflow.run_environment
            elif workflow_send_type == SEND_ID_WITH_OTHER_RUN_ENVIRONMENT:
                run_environment = run_environment_factory(created_by_group=user.groups.first())
            elif workflow_send_type == SEND_ID_IN_WRONG_GROUP:
                group = group_factory()
                set_group_access_level(user=user, group=group,
                        access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
                run_environment = run_environment_factory(created_by_group=group)

            # TODO set created by group from run_environment
            if workflow is None:
                assert run_environment is not None
                workflow = workflow_factory(
                        created_by_group=run_environment.created_by_group,
                        run_environment=run_environment)

            request_data['workflow'] = {
                'uuid': str(workflow.uuid)
            }

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
def test_workflow_execution_fetch(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory, workflow_factory,
        workflow_execution_factory, api_client) -> None:
    user = user_factory()
    workflow_execution, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_execution_factory=workflow_execution_factory,
            api_client=api_client)

    response = client.get(url)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        ensure_serialized_workflow_execution_valid(response_workflow_execution=response.data,
          workflow_execution=workflow_execution, user=user,
          group_access_level=group_access_level,
          api_key_access_level=api_key_access_level,
          api_key_run_environment=api_key_run_environment)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  body_uuid_type, workflow_send_type,
  status_code, validation_error_attribute, error_code
""", [
  # Workflow Execution with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

  # Developer with unscoped API Key fails with 400 when Workflow is
  # specifically empty
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_NONE, SEND_ID_NONE,
   400, 'workflow', 'null'),

  # Workflow Execution with unscoped API Key succeeds when Workflow is specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_NONE,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

  # non-existent uuid is present in request body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, SEND_ID_CORRECT,
   400, 'uuid', 'not_allowed'),

  # uuid of existing Workflow Execution is present in request body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_WRONG, SEND_ID_CORRECT,
   400, 'uuid', 'not_allowed'),

   # Developer with unscoped API Key cannot attach a Workflow in the
   # wrong Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_NONE, SEND_ID_IN_WRONG_GROUP,
   422, 'workflow', 'not_found'),

   # Workflow Execution with scoped API Key succeeds when Workflow is scoped
   # with the same Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

   # Developer with scoped API Key fails when Workflow is omitted
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, None,
   400, 'workflow', 'required'),

   # Developer with scoped API Key cannot create Workflow Execution with no
   # Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_NONE,
   400, 'workflow', 'null'),

   # Developer with scoped API Key cannot create Workflow Execution with a
   # Workflow in another Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'workflow', 'not_found'),

  # Support user with API Key with Observer access level fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   403, None, None),

  # Admin with API Key with observer access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   403, None, None),

  # Workflow with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

  # Support user with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

  # Observer with JWT token fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   403, None, None),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   401, None, None),
])
@mock_ecs
@mock_sts
@mock_events
def test_workflow_execution_create_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        body_uuid_type: str, workflow_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        error_code: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, workflow_execution_factory,
        api_client) -> None:
    """
    This only tests access control to the CREATE endpoint, not the actual changes.
    """

    user = user_factory()

    workflow_execution, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_execution_factory=workflow_execution_factory,
            api_client=api_client)

    request_data = make_request_body(uuid_send_type=body_uuid_type,
            workflow_send_type=workflow_send_type,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            workflow_execution=workflow_execution,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_execution_factory=workflow_execution_factory)

    old_count = WorkflowExecution.objects.count()

    response = client.post(url, data=request_data)

    assert response.status_code == status_code

    new_count = WorkflowExecution.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1

        response_workflow_execution = cast(Dict[str, Any], response.data)
        workflow_execution_uuid = response_workflow_execution['uuid']
        created_am = WorkflowExecution.objects.get(uuid=workflow_execution_uuid)

        assert group_access_level is not None
        ensure_serialized_workflow_execution_valid(
                response_workflow_execution=response_workflow_execution,
                workflow_execution=created_am, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)
    else:
        assert new_count == old_count
        check_validation_error(response, validation_error_attribute, error_code)

@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_workflow_execution_create_history_purging(
        subscription_plan, user_factory, group_factory, run_environment_factory,
        workflow_factory, workflow_execution_factory,
        api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    workflow_execution, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_scope_type=SCOPE_TYPE_CORRECT,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_execution_factory=workflow_execution_factory,
            api_client=api_client)

    request_data = make_request_body(uuid_send_type=SEND_ID_NONE,
            workflow_send_type=SEND_ID_CORRECT,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=None,
            workflow_execution=workflow_execution,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_execution_factory=workflow_execution_factory)

    workflow = workflow_execution.workflow

    utc_now = timezone.now()
    completed_workflow_execution_ids: List[int] = []
    for i in range(3):
        we = workflow_execution_factory(workflow=workflow,
                status=random.choice(WorkflowExecution.COMPLETED_STATUSES),
                finished_at = utc_now - timedelta(minutes=i))
        we.save()
        completed_workflow_execution_ids.append(we.id)

    utc_now = timezone.now()

    subscription = Subscription(group=group,
          subscription_plan=subscription_plan, active=True,
          start_at=utc_now - timedelta(minutes=1))
    subscription.save()

    plan = subscription.subscription_plan
    assert plan is not None
    plan.max_workflow_execution_history_items = 3
    plan.save()

    response = client.post(url, data=request_data)

    assert response.status_code == 201
    assert WorkflowExecution.objects.count() == 3

    for i in range(3):
        id = completed_workflow_execution_ids[i]
        exists = (WorkflowExecution.objects.filter(id=id).count() == 1)
        if i < 1:
            assert exists
        else:
            assert not exists

@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  request_uuid_send_type, body_uuid_send_type,
  workflow_send_type,
  status_code, validation_error_attribute, error_code
""", [
  # Admin with unscoped API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Developer with unscoped API Key succeeds when UUID in body matches
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   SEND_ID_CORRECT,
   200, None, None),

  # Developer with unscoped API Key fails with 422 when UUID in body does not match
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_WRONG,
   None,
   422, 'uuid', 'invalid'),

  # Developer with unscoped API Key fails with 400 when Workflow is
  # specifically empty
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_NONE,
   400, 'workflow', 'null'),

  # Developer with unscoped API Key cannot attach a Workflow in the
  # wrong Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_IN_WRONG_GROUP,
   422, 'workflow', 'not_found'),

  # Workflow with properly scoped API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK, None,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Support with properly scoped API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Observer with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   SEND_ID_CORRECT, None,
   None,
   403, None, None),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   SEND_ID_CORRECT, None,
   None,
   403, None, None),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Support user with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Observer with JWT token fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   SEND_ID_CORRECT, None,
   None,
   403, None, None),

  # Workflow with API key scoped to correct Run Environment,
  # same Run Environment in request succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   200, None, None),

  # Workflow Execution with API key scoped to correct Run Environment,
  # omits Workflow in body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Developer with developer API key scoped to a Run Environment gets 400
  # when specifying a different Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_OTHER,
   422, 'workflow', 'invalid'),

  # Developer with developer API key scoped to a Run Environment gets 404
  # when updating a Workflow Execution which has a Workflow scoped to a different
  # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   404, None, None),

  # Workflow Execution with API key scoped to a Run Environment gets
  # validation error when specifying a Workflow in another Run Environment to
  # replace the existing Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'workflow', 'not_found'),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, None,
   None,
   404, None, None),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_IN_WRONG_GROUP, None,
   None,
   404, None, None),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, None,
   None,
   401, None, None),
])
@mock_ecs
@mock_sts
@mock_events
def test_workflow_execution_update_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        request_uuid_send_type: str, body_uuid_send_type: Optional[str],
        workflow_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        error_code: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, workflow_execution_factory,
        api_client) -> None:
    """
    This only tests access control to the PATCH endpoint, not the actual changes.
    """

    user = user_factory()

    workflow_execution, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=request_uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_execution_factory=workflow_execution_factory,
            api_client=api_client)

    request_data = make_request_body(uuid_send_type=body_uuid_send_type,
            workflow_send_type=workflow_send_type,
            user=user,
            api_key_run_environment=api_key_run_environment,
            workflow_execution=workflow_execution,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_execution_factory=workflow_execution_factory)

    old_count = WorkflowExecution.objects.count()

    response = client.patch(url, request_data)

    assert response.status_code == status_code
    assert WorkflowExecution.objects.count() == old_count

    workflow_execution.refresh_from_db()

    if status_code == 200:
        assert group_access_level is not None

        ensure_serialized_workflow_execution_valid(
                response_workflow_execution=cast(Dict[str, Any], response.data),
                workflow_execution=workflow_execution, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)
    else:
        check_validation_error(response, validation_error_attribute, error_code)

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
def test_workflow_execution_delete(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        workflow_factory, workflow_execution_factory, api_client) -> None:
    user = user_factory()

    workflow_execution, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_execution_factory=workflow_execution_factory,
            api_client=api_client)

    response = client.delete(url)

    assert response.status_code == status_code

    exists = WorkflowExecution.objects.filter(pk=workflow_execution.pk).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists
