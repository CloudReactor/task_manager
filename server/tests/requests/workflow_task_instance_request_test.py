from typing import Any, Dict, List, Optional, Tuple

import uuid
from urllib.parse import quote

from django.contrib.auth.models import User

from processes.models import (
  WorkflowTaskInstance, Workflow,
  Task, RunEnvironment,
  UserGroupAccessLevel
)

from processes.serializers import (
    WorkflowTaskInstanceSerializer
)

import pytest

from rest_framework.test import APIClient

from moto import mock_ecs, mock_sts, mock_events

from conftest import *


def ensure_serialized_workflow_task_instance_valid(response_workflow_task_instance: Dict[str, Any],
        workflow_task_instance: WorkflowTaskInstance, user: User,
        group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> None:
    context = context_with_authenticated_request(user=user,
            group=workflow_task_instance.workflow.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    assert response_workflow_task_instance == WorkflowTaskInstanceSerializer(
              workflow_task_instance, context=context).data

    if api_key_run_environment:
        assert workflow_task_instance.workflow.run_environment is not None
        assert api_key_run_environment.pk == workflow_task_instance.workflow.run_environment.pk

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


  ### Failing
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
def test_workflow_task_instance_list(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        user_has_another_group: bool, send_group_id_type: str,
        send_workflow_uuid_type: str,
        status_code: int, expected_indices: List[int],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, workflow_task_instance_factory, api_client) -> None:
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

    workflow_task_instances = [
      workflow_task_instance_factory(workflow=production_workflow),
      workflow_task_instance_factory(workflow=test_workflow)
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

    response = client.get('/api/v1/workflow_task_instances/', params)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        page = response.data
        assert page['count'] == len(expected_indices)
        results = page['results']

        for i in expected_indices:
            response_workflow_task_instance = results[i]
            target_workflow_task_instance = workflow_task_instances[expected_indices[i]]
            ensure_serialized_workflow_task_instance_valid(response_workflow_task_instance,
                    workflow_task_instance=target_workflow_task_instance, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)


def common_setup(is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str, existing_has_run_environment: bool,
        user, group_factory, run_environment_factory,
        workflow_factory, workflow_task_instance_factory, api_client) \
        -> Tuple[WorkflowTaskInstance, Optional[RunEnvironment], APIClient, str]:
    group = user.groups.first()

    if group_access_level is not None:
        set_group_access_level(user=user, group=group,
                access_level=group_access_level)

    workflow_task_instance_group = group

    workflow_run_environment = None

    if existing_has_run_environment:
        workflow_run_environment = run_environment_factory(
                created_by_group=workflow_task_instance_group)

    another_run_environment = run_environment_factory(created_by_group=workflow_task_instance_group)

    workflow = workflow_factory(created_by_group=group, run_environment=workflow_run_environment)

    workflow_task_instance = workflow_task_instance_factory(workflow=workflow)

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = workflow_run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = another_run_environment

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    url = '/api/v1/workflow_task_instances/'

    if uuid_send_type != SEND_ID_NONE:
        workflow_task_instance_uuid = uuid.uuid4()
        if uuid_send_type == SEND_ID_CORRECT:
            workflow_task_instance_uuid = workflow_task_instance.uuid
        elif uuid_send_type == SEND_ID_IN_WRONG_GROUP:
            another_group = group_factory()
            set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
            workflow_in_other_group = workflow_factory(created_by_group=another_group)
            workflow_task_instance_in_other_group = workflow_task_instance_factory(
                    workflow=workflow_in_other_group)
            workflow_task_instance_uuid = workflow_task_instance_in_other_group.uuid

        url += quote(str(workflow_task_instance_uuid)) + '/'

    return (workflow_task_instance, api_key_run_environment, client, url)

def make_request_body(uuid_send_type: Optional[str],
        workflow_send_type: Optional[str], task_send_type: Optional[str],
        user: User,
        api_key_run_environment: Optional[RunEnvironment],
        workflow_task_instance: WorkflowTaskInstance,
        group_factory, run_environment_factory, workflow_factory,
        task_factory, workflow_task_instance_factory) -> Dict[str, Any]:
    request_data: Dict[str, Any] = {
      'name': 'WTI_1'
    }

    if uuid_send_type == SEND_ID_NOT_FOUND:
        request_data['uuid'] = str(uuid.uuid4())
    elif uuid_send_type == SEND_ID_CORRECT:
        request_data['uuid'] = str(workflow_task_instance.uuid)
    elif uuid_send_type == SEND_ID_WRONG:
        another_workflow_task_instance = workflow_task_instance_factory(
                workflow=workflow_task_instance.workflow)
        request_data['uuid'] = str(another_workflow_task_instance.uuid)

    workflow_run_environment: Optional[RunEnvironment] = None
    task_run_environment: Optional[RunEnvironment] = None

    if workflow_send_type is None:
        workflow_run_environment = workflow_task_instance.workflow.run_environment
    else:
        workflow: Optional[Workflow] = None
        if workflow_send_type == SEND_ID_NONE:
            request_data['workflow'] = None
        else:
            if workflow_send_type == SEND_ID_CORRECT:
                if api_key_run_environment:
                    workflow_run_environment = api_key_run_environment
                else:
                    workflow_run_environment = workflow_task_instance.workflow.run_environment

                workflow = workflow_task_instance.workflow
            elif workflow_send_type == SEND_ID_OTHER:
                workflow_run_environment = workflow_task_instance.workflow.run_environment
            elif workflow_send_type == SEND_ID_WITH_OTHER_RUN_ENVIRONMENT:
                workflow_run_environment = run_environment_factory(created_by_group=user.groups.first())
            elif workflow_send_type == SEND_ID_IN_WRONG_GROUP:
                group = group_factory()
                set_group_access_level(user=user, group=group,
                        access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
                workflow_run_environment = run_environment_factory(created_by_group=group)

            # TODO set created by group from run_environment
            if workflow is None:
                assert workflow_run_environment is not None
                workflow = workflow_factory(
                    created_by_group=workflow_run_environment.created_by_group,
                    run_environment=workflow_run_environment)

            request_data['workflow'] = {
                'uuid': str(workflow.uuid)
            }

    task_group = user.groups.first()
    task_run_environment = workflow_run_environment or \
        run_environment_factory(created_by_group=task_group)

    task: Optional[Task] = None
    if task_send_type == SEND_ID_CORRECT:
        pass
    elif task_send_type == SEND_ID_WRONG:
        task = task_factory()
    elif task_send_type == SEND_ID_IN_WRONG_GROUP:
        task_group = group_factory()
        assert task_group is not None # for my
        set_group_access_level(user=user, group=task_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
    elif task_send_type == SEND_ID_WITH_OTHER_RUN_ENVIRONMENT:
        task_run_environment = run_environment_factory(created_by_group=task_group)

    if task is None:
        assert task_run_environment is not None
        task = task_factory(
              created_by_group=task_run_environment.created_by_group,
              run_environment=task_run_environment)

    request_data['task'] = {
        'uuid': str(task.uuid)
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
def test_workflow_task_instance_fetch(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory, workflow_factory,
        task_factory, workflow_task_instance_factory, api_client) -> None:
    user = user_factory()
    workflow_task_instance, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            existing_has_run_environment=True,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_task_instance_factory=workflow_task_instance_factory,
            api_client=api_client)

    response = client.get(url)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        ensure_serialized_workflow_task_instance_valid(response_workflow_task_instance=response.data,
          workflow_task_instance=workflow_task_instance, user=user,
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
  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

  # Developer with unscoped API Key fails with 400 when Workflow is
  # specifically empty
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_NONE, SEND_ID_NONE,
   400, 'workflow', 'null'),

  # Developer with unscoped API Key succeeds when Workflow is specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

  # non-existent uuid is present in request body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, SEND_ID_CORRECT,
   400, 'uuid', 'not_allowed'),

  # uuid of existing Workflow Task Instance is present in request body
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

   # Workflow Task Instance with scoped API Key succeeds when Workflow is scoped
   # with the same Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_CORRECT,
   201, None, None),

   # Developer with scoped API Key fails when Workflow is omitted
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, None,
   400, 'workflow', 'required'),

   # Developer with scoped API Key cannot create Workflow Task Instance with no
   # Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_NONE,
   400, 'workflow', 'null'),

   # Developer with scoped API Key cannot create Workflow Task Instance with a
   # Workflow in another Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'workflow', 'not_found'),

  # Support user with API Key with support access fails with 403
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
def test_workflow_task_instance_create_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        body_uuid_type: str, workflow_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        error_code: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, task_factory, workflow_task_instance_factory,
        api_client) -> None:
    """
    This only tests access control to the CREATE endpoint, not the actual changes.
    """

    user = user_factory()

    workflow_task_instance, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=SEND_ID_NONE,
            existing_has_run_environment=True,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_task_instance_factory=workflow_task_instance_factory,
            api_client=api_client)

    request_data = make_request_body(uuid_send_type=body_uuid_type,
            workflow_send_type=workflow_send_type,
            task_send_type=SEND_ID_CORRECT,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            workflow_task_instance=workflow_task_instance,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            task_factory=task_factory,
            workflow_task_instance_factory=workflow_task_instance_factory)

    old_count = WorkflowTaskInstance.objects.count()

    response = client.post(url, data=request_data)

    assert response.status_code == status_code

    new_count = WorkflowTaskInstance.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1

        response_workflow_task_instance = cast(Dict[str, Any], response.data)
        workflow_task_instance_uuid = response_workflow_task_instance['uuid']
        created_am = WorkflowTaskInstance.objects.get(uuid=workflow_task_instance_uuid)

        assert group_access_level is not None
        ensure_serialized_workflow_task_instance_valid(
                response_workflow_task_instance=response_workflow_task_instance,
                workflow_task_instance=created_am, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)
    else:
        assert new_count == old_count
        check_validation_error(response, validation_error_attribute, error_code)

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

  # Developer with developer API key scoped to a Run Environment gets 400
  # when specifying a different Workflow
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, None,
   SEND_ID_OTHER,
   422, 'workflow', 'invalid'),

  # Developer with developer API key scoped to a Run Environment gets 404
  # when updating a Workflow Task Instance which has a Workflow scoped to a different
  # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, None,
   SEND_ID_CORRECT,
   404, None, None),

  # Workflow Task Instance with API key scoped to a Run Environment gets
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
def test_workflow_task_instance_update_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        request_uuid_send_type: str, body_uuid_send_type: Optional[str],
        workflow_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        error_code: Optional[str],
        user_factory, group_factory, run_environment_factory,
        workflow_factory, task_factory, workflow_task_instance_factory,
        api_client) -> None:
    """
    This only tests access control to the PATCH endpoint, not the actual changes.
    """

    user = user_factory()

    workflow_task_instance, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=request_uuid_send_type,
            existing_has_run_environment=True,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_task_instance_factory=workflow_task_instance_factory,
            api_client=api_client)

    request_data = make_request_body(uuid_send_type=body_uuid_send_type,
            workflow_send_type=workflow_send_type,
            task_send_type=SEND_ID_CORRECT,
            user=user,
            api_key_run_environment=api_key_run_environment,
            workflow_task_instance=workflow_task_instance,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            task_factory=task_factory,
            workflow_task_instance_factory=workflow_task_instance_factory)

    old_count = WorkflowTaskInstance.objects.count()

    response = client.patch(url, request_data)

    assert response.status_code == status_code
    assert WorkflowTaskInstance.objects.count() == old_count

    workflow_task_instance.refresh_from_db()

    if status_code == 200:
        assert group_access_level is not None

        ensure_serialized_workflow_task_instance_valid(
                response_workflow_task_instance=cast(Dict[str, Any], response.data),
                workflow_task_instance=workflow_task_instance, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)
    else:
        check_validation_error(response, validation_error_attribute, error_code)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  api_key_access_level, api_key_scope_type,
  task_send_type, existing_has_run_environment,
  status_code
""", [
  # Developer authenticated with JWT succeeds with scoped Run Environment
  # where Task is scoped
  (None, None,
   SEND_ID_CORRECT, False,
   201),

  # Developer authenticated with JWT succeeds with an unscoped Workflow
  # where Task is scoped to another Run Environment.
  # Existing is unscoped.
  (None, None,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT, False,
   201),

  # Developer authenticated with JWT succeeds with Workflow scoped to a Run Environment
  # where Task is scoped correctly
  (None, None,
   SEND_ID_CORRECT, True,
   201),

  # Developer authenticated with JWT gets 422 with a Worklow scoped to a Run Environment
  # where Task is scoped to a different run environment
  (None, None,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT, True,
   422),

  # Developer with unscoped API Key succeeds where Workflow in unscoped.
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, False,
   201),

  # Developer with unscoped API Key succeeds where Workflow is scoped.
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_CORRECT, True,
   201),

 # Developer with unscoped API Key succeeds when Task Run Environment
 # matches Task Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_OTHER, True,
   201),

 # Developer with unscoped API Key fails when Workflow Run Environment
 # does not match Task Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT, True,
   422),

  # Developer with scoped API Key succeeds with correct Run Environment
  # and an Task that scoped to the same Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, True,
   201),

  # Developer with scoped API Key fails using scoped Workflow and
  # Task with different Run Environment
  (UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT, True,
   422),
])
@mock_ecs
@mock_sts
@mock_events
def test_workflow_set_task(
        api_key_access_level: Optional[int], api_key_scope_type: str,
        task_send_type: Optional[str], existing_has_run_environment: bool,
        status_code: int,
        user_factory, group_factory, run_environment_factory, task_factory,
        workflow_task_instance_factory, workflow_factory,
        api_client) -> None:
    """
    Tests for setting Task.
    """
    group_access_level = UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER

    user = user_factory()

    for is_post in [True, False]:
        uuid_send_type = SEND_ID_NONE if is_post else SEND_ID_CORRECT

        wti, api_key_run_environment, client, url = common_setup(
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
                workflow_task_instance_factory=workflow_task_instance_factory,
                api_client=api_client)

        old_count = WorkflowTaskInstance.objects.count()

        request_data = make_request_body(
                uuid_send_type=None,
                workflow_send_type=SEND_ID_CORRECT,
                task_send_type=task_send_type,
                user=user,
                group_factory=group_factory,
                api_key_run_environment=api_key_run_environment,
                workflow_task_instance=wti,
                run_environment_factory=run_environment_factory,
                task_factory=task_factory,
                workflow_task_instance_factory=workflow_task_instance_factory,
                workflow_factory=workflow_factory)

        if is_post:
            response = client.post(url, data=request_data)
        else:
            # Prevent conflict with previous iteration's created entity
            request_data['name'] = 'Updated WTI'
            response = client.patch(url, data=request_data)

        actual_status_code = status_code

        if status_code == 201 and not is_post:
            actual_status_code = 200

        assert response.status_code == actual_status_code

        new_count = WorkflowTaskInstance.objects.count()

        if status_code == 201:
            if is_post:
                assert new_count == old_count + 1
            else:
                assert new_count == old_count

            response_wti = cast(Dict[str, Any], response.data)
            assert response_wti

            wti_uuid = response_wti['uuid']
            created_wti = WorkflowTaskInstance.objects.get(uuid=wti_uuid)

            assert group_access_level is not None
            ensure_serialized_workflow_task_instance_valid(
                    response_workflow_task_instance=response_wti,
                    workflow_task_instance=created_wti, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)

            assert(response_wti['task']['uuid'] == str(created_wti.task.uuid))
        else:
            assert new_count == old_count

            if status_code == 422:
                response_dict = cast(Dict[str, Any], response.data)
                assert('task' in response_dict)

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
def test_workflow_task_instance_delete(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        workflow_factory, task_factory, workflow_task_instance_factory,
        api_client) -> None:
    user = user_factory()

    workflow_task_instance, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            existing_has_run_environment=True,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            workflow_factory=workflow_factory,
            workflow_task_instance_factory=workflow_task_instance_factory,
            api_client=api_client)

    response = client.delete(url)

    assert response.status_code == status_code

    exists = WorkflowTaskInstance.objects.filter(pk=workflow_task_instance.pk).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists
