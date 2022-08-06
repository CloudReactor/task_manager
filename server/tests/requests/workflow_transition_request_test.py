from typing import Any, List, Optional, Tuple, cast

import uuid
from urllib.parse import quote

from django.contrib.auth.models import User

from processes.models import (
  RunEnvironment, Workflow, WorkflowTransition, UserGroupAccessLevel
)

from processes.serializers import (
    WorkflowTransitionSerializer
)

import pytest

from rest_framework.test import APIClient

from moto import mock_ecs, mock_sts, mock_events

from conftest import *


def ensure_serialized_workflow_transition_valid(response_workflow_transition: dict[str, Any],
        workflow_transition: WorkflowTransition, user: User,
        group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> None:
    context = context_with_authenticated_request(user=user,
            group=workflow_transition.workflow.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    assert response_workflow_transition == WorkflowTransitionSerializer(
              workflow_transition, context=context).data

    if api_key_run_environment:
        assert api_key_run_environment.pk == workflow_transition.workflow.run_environment.pk

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
@mock_ecs
@mock_sts
@mock_events
def test_workflow_transition_list(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        user_has_another_group: bool, send_group_id_type: str,
        send_workflow_uuid_type: str,
        status_code: int, expected_indices: List[int],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, workflow_task_instance_factory, task_factory,
        workflow_transition_factory, api_client) -> None:
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
    production_from_wti = workflow_task_instance_factory(workflow=production_workflow,
            task=task_factory(run_environment=production_run_environment,
            created_by_group=workflow_group))
    production_to_wti = workflow_task_instance_factory(workflow=production_workflow,
            task=task_factory(run_environment=production_run_environment,
            created_by_group=workflow_group))

    test_run_environment = run_environment_factory(created_by_group=workflow_group)
    test_workflow = workflow_factory(created_by_group=workflow_group,
        run_environment=test_run_environment)
    test_from_wti = workflow_task_instance_factory(workflow=test_workflow,
            task=task_factory(run_environment=test_run_environment,
            created_by_group=workflow_group))
    test_to_wti = workflow_task_instance_factory(workflow=test_workflow,
            task=task_factory(run_environment=test_run_environment,
            created_by_group=workflow_group))

    workflow_transitions = sorted([
      workflow_transition_factory(from_workflow_task_instance=test_from_wti,
              to_workflow_task_instance=test_to_wti),
      workflow_transition_factory(from_workflow_task_instance=production_from_wti,
              to_workflow_task_instance=production_to_wti),
    ], key=lambda wt: str(wt.uuid))

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = workflow_transitions[0].to_workflow_task_instance.workflow.run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = workflow_transitions[1].to_workflow_task_instance.workflow.run_environment

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
        workflow_uuid = str(workflow_transitions[0].workflow.uuid)
    elif send_workflow_uuid_type == SEND_ID_NOT_FOUND:
        workflow_uuid = 'abc'

    if workflow_uuid:
        params['workflow__uuid'] = workflow_uuid

    response = client.get('/api/v1/workflow_transitions/', params)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        page = response.data
        assert page['count'] == len(expected_indices)
        results = page['results']

        for i in expected_indices:
            response_workflow_transition = results[i]
            target_workflow_transition = workflow_transitions[expected_indices[i]]
            ensure_serialized_workflow_transition_valid(response_workflow_transition,
                    workflow_transition=target_workflow_transition, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)


def common_setup(is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str, existing_has_run_environment: bool,
        create_existing: bool,
        user, group_factory, run_environment_factory,
        workflow_factory, workflow_task_instance_factory, task_factory,
        workflow_transition_factory, api_client) \
        -> Tuple[Optional[WorkflowTransition], Workflow, Optional[RunEnvironment], APIClient, str]:
    group = user.groups.first()

    if group_access_level is not None:
        set_group_access_level(user=user, group=group,
                access_level=group_access_level)

    workflow_transition_group = group

    workflow_run_environment = None

    if existing_has_run_environment:
        workflow_run_environment = run_environment_factory(
                created_by_group=workflow_transition_group)

    another_run_environment = run_environment_factory(created_by_group=workflow_transition_group)

    workflow = workflow_factory(created_by_group=group, run_environment=workflow_run_environment)

    from_wti = workflow_task_instance_factory(workflow=workflow)
    to_wti = workflow_task_instance_factory(workflow=workflow)

    workflow_transition: Optional[WorkflowTransition] = None

    if create_existing:
        workflow_transition = workflow_transition_factory(
              from_workflow_task_instance=from_wti,
              to_workflow_task_instance=to_wti)

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = workflow_run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = another_run_environment

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    url = '/api/v1/workflow_transitions/'

    if uuid_send_type != SEND_ID_NONE:
        workflow_transition_uuid = uuid.uuid4()
        if uuid_send_type == SEND_ID_CORRECT:
            workflow_transition_uuid = cast(WorkflowTransition, workflow_transition).uuid
        elif uuid_send_type == SEND_ID_IN_WRONG_GROUP:
            another_group = group_factory()
            set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
            workflow_in_other_group = workflow_factory(created_by_group=another_group)

            from_wti_in_other_group = workflow_task_instance_factory(
                    workflow=workflow_in_other_group,
                    task=task_factory(created_by_group=another_group))

            to_wti_in_other_group = workflow_task_instance_factory(
                    workflow=workflow_in_other_group,
                    task=task_factory(created_by_group=another_group))

            workflow_transition_in_other_group = workflow_transition_factory(
                    from_workflow_task_instance=from_wti_in_other_group,
                    to_workflow_task_instance=to_wti_in_other_group)

            workflow_transition_uuid = workflow_transition_in_other_group.uuid

        url += quote(str(workflow_transition_uuid)) + '/'

    return (workflow_transition, workflow, api_key_run_environment, client, url)

def make_request_body(uuid_send_type: Optional[str],
        wti_send_type: Optional[str],
        for_from_wti: bool,
        user: User,
        api_key_run_environment: Optional[RunEnvironment],
        workflow_transition: Optional[WorkflowTransition],
        workflow: Workflow,
        group_factory, run_environment_factory, workflow_factory,
        workflow_task_instance_factory, task_factory,
        workflow_transition_factory) -> dict[str, Any]:
    request_data: dict[str, Any] = {
        'rule_type': WorkflowTransition.RULE_TYPE_ON_SUCCESS
    }

    if uuid_send_type == SEND_ID_NOT_FOUND:
        request_data['uuid'] = str(uuid.uuid4())
    elif uuid_send_type == SEND_ID_CORRECT:
        request_data['uuid'] = str(cast(WorkflowTransition, workflow_transition).uuid)
    elif uuid_send_type == SEND_ID_WRONG:
        another_workflow_transition = workflow_transition_factory()
        request_data['uuid'] = str(another_workflow_transition.uuid)

    good_wti_prefix = 'to' if for_from_wti else 'from'
    varying_wti_prefix = 'from' if for_from_wti else 'to'

    varying_task_run_environment: Optional[RunEnvironment] = None

    workflow_run_environment = workflow.run_environment
    varying_task_run_environment = workflow_run_environment
    group = workflow.created_by_group

    good_task = task_factory(
          created_by_group=group,
          run_environment=varying_task_run_environment)

    good_wti = workflow_task_instance_factory(workflow=workflow,
        task=good_task)

    request_data[f'{good_wti_prefix}_workflow_task_instance'] = {
        'uuid': str(good_wti.uuid)
    }

    if wti_send_type is None:
        pass
    else:
        if wti_send_type == SEND_ID_NONE:
            request_data[f'{varying_wti_prefix}_workflow_task_instance'] = None
        else:
            if wti_send_type == SEND_ID_CORRECT:
                if api_key_run_environment:
                    workflow_run_environment = api_key_run_environment
            elif wti_send_type == SEND_ID_WRONG:
                workflow = workflow_factory()
            elif wti_send_type == SEND_ID_WITH_OTHER_RUN_ENVIRONMENT:
                workflow_run_environment = run_environment_factory(created_by_group=user.groups.first())
                workflow = workflow_factory(run_environment=workflow_run_environment,
                        created_by_group=group)
            elif wti_send_type == SEND_ID_IN_WRONG_GROUP:
                group = group_factory()
                set_group_access_level(user=user, group=group,
                        access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
                workflow_run_environment = run_environment_factory(created_by_group=group)
                workflow = workflow_factory(run_environment=workflow_run_environment,
                        created_by_group=group)

    varying_task_group = group
    varying_task_run_environment = workflow_run_environment or \
        run_environment_factory(created_by_group=varying_task_group)

    varying_task = task_factory(
          created_by_group=varying_task_run_environment.created_by_group,
          run_environment=varying_task_run_environment)

    if wti_send_type and (wti_send_type != SEND_ID_NONE):
        varying_wti = workflow_task_instance_factory(workflow=workflow, task=varying_task)

        request_data[f'{varying_wti_prefix}_workflow_task_instance'] = {
            'uuid': str(varying_wti.uuid)
        }

    print(f"{request_data=}")

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
def test_workflow_transition_fetch(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory, workflow_factory,
        workflow_task_instance_factory, task_factory,
        workflow_transition_factory, api_client) -> None:
    user = user_factory()
    workflow_transition, _workflow, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            existing_has_run_environment=True,
            create_existing=True,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_task_instance_factory=workflow_task_instance_factory,
            task_factory=task_factory,
            workflow_transition_factory=workflow_transition_factory,
            api_client=api_client)

    response = client.get(url)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        ensure_serialized_workflow_transition_valid(response_workflow_transition=response.data,
          workflow_transition=cast(WorkflowTransition, workflow_transition),
          user=user,
          group_access_level=group_access_level,
          api_key_access_level=api_key_access_level,
          api_key_run_environment=api_key_run_environment)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  body_uuid_type, wti_send_type,
  status_code, validation_error_attribute, error_code
""", [
  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

  # Developer with unscoped API Key fails with 400 when Workflow Task Instance is
  # specifically empty
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_NONE, SEND_ID_NONE,
   400, 'from_workflow_task_instance', 'null'),

  # Developer with unscoped API Key succeeds when Workflow Task Instance is specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

  # non-existent uuid is present in request body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, SEND_ID_CORRECT,
   400, 'uuid', 'not_allowed'),

  # uuid of existing Workflow Transition is present in request body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_WRONG, SEND_ID_CORRECT,
   400, 'uuid', 'not_allowed'),

   # Developer with unscoped API Key cannot attach to a Workflow in the
   # wrong Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_NONE, SEND_ID_IN_WRONG_GROUP,
   422, 'from_workflow_task_instance', 'not_found'),

   # Workflow Transition with scoped API Key succeeds when Workflow is scoped
   # with the same Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

   # Developer with scoped API Key fails when Workflow Task Instance is omitted
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, None,
   400, 'from_workflow_task_instance', 'required'),

   # Developer with scoped API Key cannot create Workflow Transition with no
   # Workflow Task Instance
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_NONE,
   400, 'from_workflow_task_instance', 'null'),

   # Developer with scoped API Key cannot create Workflow Transition with a
   # Workflow in another Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'from_workflow_task_instance', 'not_found'),

  # Developer user with API Key with support access level fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   403, None, None),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   403, None, None),

  # Workflow with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

  # Support user with JWT token fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
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
def test_workflow_transition_create_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        body_uuid_type: str, wti_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        error_code: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, task_factory, workflow_task_instance_factory,
        workflow_transition_factory,
        api_client) -> None:
    """
    This only tests access control to the CREATE endpoint, not the actual changes.
    """
    for for_from_wti in [True, False]:
        user = user_factory()

        workflow_transition, workflow, api_key_run_environment, client, url = common_setup(
                is_authenticated=is_authenticated,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_scope_type=api_key_scope_type,
                uuid_send_type=SEND_ID_NONE,
                existing_has_run_environment=True,
                create_existing=False,
                user=user,
                group_factory=group_factory,
                run_environment_factory=run_environment_factory,
                workflow_factory=workflow_factory,
                workflow_task_instance_factory=workflow_task_instance_factory,
                task_factory=task_factory,
                workflow_transition_factory=workflow_transition_factory,
                api_client=api_client)

        request_data = make_request_body(uuid_send_type=body_uuid_type,
                wti_send_type=wti_send_type,
                for_from_wti=for_from_wti,
                user=user,
                group_factory=group_factory,
                api_key_run_environment=api_key_run_environment,
                workflow_transition=workflow_transition,
                workflow=workflow,
                run_environment_factory=run_environment_factory,
                workflow_factory=workflow_factory,
                workflow_task_instance_factory=workflow_task_instance_factory,
                task_factory=task_factory,
                workflow_transition_factory=workflow_transition_factory)

        old_count = WorkflowTransition.objects.count()

        response = client.post(url, data=request_data)

        assert response.status_code == status_code

        new_count = WorkflowTransition.objects.count()

        if status_code == 201:
            assert new_count == old_count + 1

            response_workflow_transition = cast(dict[str, Any], response.data)
            workflow_transition_uuid = response_workflow_transition['uuid']
            created_am = WorkflowTransition.objects.get(uuid=workflow_transition_uuid)

            assert group_access_level is not None
            ensure_serialized_workflow_transition_valid(
                    response_workflow_transition=response_workflow_transition,
                    workflow_transition=created_am, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)
        else:
            assert new_count == old_count

            if validation_error_attribute:
                actual_vea = validation_error_attribute

                if (not for_from_wti) and \
                        (validation_error_attribute == 'from_workflow_task_instance'):
                    actual_vea = 'to_workflow_task_instance'

                response_dict = cast(dict[str, Any], response.data)
                assert(actual_vea in response_dict)

                if error_code:
                    assert(response_dict[actual_vea][0].code == error_code)

@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  request_uuid_send_type, body_uuid_send_type,
  wti_send_type,
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
   400, 'from_workflow_task_instance', 'null'),

  # Developer with unscoped API Key cannot attach a Workflow in the
  # wrong Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_IN_WRONG_GROUP,
   422, 'from_workflow_task_instance', 'not_found'),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, None,
   None,
   403, None, None),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, None,
   None,
   403, None, None),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
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

  # Developer with API key scoped to correct Run Environment,
  # same Run Environment in request succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   200, None, None),

  # Developer with API key scoped to correct Run Environment,
  # omits Workflow in body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   None,
   200, None, None),

  # Developer with developer API key scoped to a Run Environment gets 422
  # when specifying an unauthorized Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_WRONG,
   422, 'from_workflow_task_instance', 'not_found'),

  # Developer with developer API key scoped to a Run Environment gets 404
  # when updating a Workflow Transition which has a Workflow scoped to a different
  # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   404, None, None),

  # Workflow Transition with API key scoped to a Run Environment gets
  # validation error when specifying a Workflow in another Run Environment to
  # replace the existing Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'from_workflow_task_instance', 'not_found'),

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
def test_workflow_transition_update_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        request_uuid_send_type: str, body_uuid_send_type: Optional[str],
        wti_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        error_code: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, task_factory, workflow_task_instance_factory,
        workflow_transition_factory,
        api_client) -> None:
    """
    This only tests access control to the PATCH endpoint, not the actual changes.
    """
    for for_from_wti in [True, False]:
        user = user_factory()

        workflow_transition, workflow, api_key_run_environment, client, url = common_setup(
                is_authenticated=is_authenticated,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_scope_type=api_key_scope_type,
                uuid_send_type=request_uuid_send_type,
                existing_has_run_environment=True,
                create_existing=True,
                user=user,
                group_factory=group_factory,
                run_environment_factory=run_environment_factory,
                workflow_factory=workflow_factory,
                workflow_task_instance_factory=workflow_task_instance_factory,
                task_factory=task_factory,
                workflow_transition_factory=workflow_transition_factory,
                api_client=api_client)

        request_data = make_request_body(uuid_send_type=body_uuid_send_type,
                wti_send_type=wti_send_type,
                for_from_wti=for_from_wti,
                user=user,
                api_key_run_environment=api_key_run_environment,
                workflow_transition=workflow_transition,
                workflow=workflow,
                group_factory=group_factory,
                run_environment_factory=run_environment_factory,
                workflow_factory=workflow_factory,
                task_factory=task_factory,
                workflow_task_instance_factory=workflow_task_instance_factory,
                workflow_transition_factory=workflow_transition_factory)

        old_count = WorkflowTransition.objects.count()

        response = client.patch(url, request_data)

        assert response.status_code == status_code
        assert WorkflowTransition.objects.count() == old_count

        workflow_transition.refresh_from_db()

        if status_code == 200:
            assert group_access_level is not None

            ensure_serialized_workflow_transition_valid(
                    response_workflow_transition=cast(dict[str, Any], response.data),
                    workflow_transition=workflow_transition, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)
        else:
            if validation_error_attribute:
                actual_vea = validation_error_attribute

                if (not for_from_wti) and \
                        (validation_error_attribute == 'from_workflow_task_instance'):
                    actual_vea = 'to_workflow_task_instance'

                response_dict = cast(dict[str, Any], response.data)
                assert actual_vea in response_dict

                if error_code:
                    assert(response_dict[actual_vea][0].code == error_code)

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
def test_workflow_transition_delete(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        workflow_factory, workflow_task_instance_factory, task_factory,
        workflow_transition_factory,
        api_client) -> None:
    user = user_factory()

    workflow_transition, _workflow, _api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            existing_has_run_environment=True,
            create_existing=True,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_task_instance_factory=workflow_task_instance_factory,
            task_factory=task_factory,
            workflow_transition_factory=workflow_transition_factory,
            api_client=api_client)

    response = client.delete(url)

    assert response.status_code == status_code

    exists = WorkflowTransition.objects.filter(
            pk=cast(WorkflowTransition, workflow_transition).pk).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists
