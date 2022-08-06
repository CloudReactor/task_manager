from typing import cast, Any, List, Optional, Tuple

import uuid
from urllib.parse import quote

from django.contrib.auth.models import User, Group

from processes.common.request_helpers import (
  context_with_request
)

from processes.models import (
  RunEnvironment, UserGroupAccessLevel
)

from processes.serializers import RunEnvironmentSerializer

import pytest

from rest_framework.test import APIClient

from conftest import *

PROTECTED_PROPERTIES = [
  'execution_method_capabilities',
  'aws_workflow_starter_access_key'
]

def ensure_serialized_run_environment_valid(response_re: dict[str, Any],
        run_environment: RunEnvironment, user: User,
        group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> None:
    context = context_with_authenticated_request(user=user,
            group=run_environment.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    assert response_re == RunEnvironmentSerializer(run_environment,
            context=context).data

    for prop in PROTECTED_PROPERTIES:
        if access_level < UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER:
            assert prop not in response_re
        else:
            assert prop in response_re

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
def test_run_environment_list(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        user_has_another_group: bool, send_group_id_type: str,
        status_code: int, expected_indices: List[int],
        user_factory, group_factory, run_environment_factory, api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    another_group = group_factory()

    if user_has_another_group:
        set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    re_group = group
    run_environments = [
      run_environment_factory(name='Production', created_by_group=re_group),
      run_environment_factory(name='Test', created_by_group=re_group)
    ]

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = run_environments[0]
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = run_environments[1]

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

    response = client.get('/api/v1/run_environments/', params)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        page = response.data
        assert page['count'] == len(expected_indices)
        results = page['results']

        for i in expected_indices:
            response_re = results[i]
            target_re = run_environments[expected_indices[i]]
            ensure_serialized_run_environment_valid(response_re,
                    run_environment=target_re, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)


def common_setup(is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str,
        user, group_factory, run_environment_factory, api_client) \
        -> Tuple[RunEnvironment, Optional[RunEnvironment], APIClient, str]:
    group = user.groups.first()

    if group_access_level is not None:
        set_group_access_level(user=user, group=group,
                access_level=group_access_level)

    re_group = group

    run_environment = run_environment_factory(created_by_group=re_group)
    another_run_environment = run_environment_factory(created_by_group=re_group)

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = another_run_environment

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    url = '/api/v1/run_environments/'

    if uuid_send_type != SEND_ID_NONE:
        re_uuid = uuid.uuid4()
        if uuid_send_type == SEND_ID_CORRECT:
            re_uuid = run_environment.uuid
        elif uuid_send_type == SEND_ID_IN_WRONG_GROUP:
            another_group = group_factory()
            set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
            run_environment_in_other_group = run_environment_factory(
                    created_by_group=another_group)
            re_uuid = run_environment_in_other_group.uuid

        url += quote(str(re_uuid)) + '/'

    return (run_environment, api_key_run_environment, client, url)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  send_uuid_type, status_code
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_CORRECT, 200),

  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, 200),

  # Observer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   SEND_ID_CORRECT, 200),

  # Admin with API Key with support access succeeds, with base fields
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, 200),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, 200),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, 200),

  # Observer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   SEND_ID_CORRECT, 200),

  # Developer with developer API key scoped to correct Run Environment, explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, 200),

  # Developer with developer API key scoped to different Run Environment gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, 404),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, 404),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_IN_WRONG_GROUP, 404),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, 401),
])
def test_run_environment_fetch(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        api_key_scope_type: str,
        send_uuid_type: str, status_code: int,
        user_factory, group_factory, run_environment_factory, api_client) -> None:
    user = user_factory()
    run_environment, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=send_uuid_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            api_client=api_client)

    response = client.get(url)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        ensure_serialized_run_environment_valid(response_re=response.data,
          run_environment=run_environment, user=user,
          group_access_level=group_access_level,
          api_key_access_level=api_key_access_level,
          api_key_run_environment=api_key_run_environment)

@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  send_uuid_type, status_code
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NONE, 201),

  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_NONE, 201),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_NONE, 403),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_NONE, 403),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_NONE, 201),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_NONE, 201),

  # Observer with JWT token fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_NONE, 403),

  # Developer with developer API key scoped to a Run Environment gets 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_NONE, 403),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_NONE, 401),
])
def test_run_environment_create_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        send_uuid_type: str, status_code: int,
        user_factory, group_factory, run_environment_factory, api_client) -> None:
    """
    This only tests access control to the CREATE endpoint, not the actual changes.
    """

    user = user_factory()

    run_environment, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=SEND_ID_NONE,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            api_client=api_client)

    old_count = RunEnvironment.objects.count()

    request_data = {
      'name': 'Some RE'
    }

    if send_uuid_type == SEND_ID_NOT_FOUND:
        request_data['uuid'] = str(uuid.uuid4())
    elif send_uuid_type == SEND_ID_WRONG:
        request_data['uuid'] = str(run_environment.uuid)

    response = client.post(url, data=request_data)

    assert response.status_code == status_code

    new_count = RunEnvironment.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1

        response_re = cast(dict[str, Any], response.data)
        re_uuid = response_re['uuid']
        created_re = RunEnvironment.objects.get(uuid=re_uuid)

        assert group_access_level is not None
        ensure_serialized_run_environment_valid(response_re=response_re,
          run_environment=created_re, user=user,
          group_access_level=group_access_level,
          api_key_access_level=api_key_access_level,
          api_key_run_environment=api_key_run_environment)
    else:
        assert new_count == old_count


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  send_uuid_type, status_code
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_CORRECT, 200),

  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, 200),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, 403),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, 403),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, 200),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, 200),

  # Observer with JWT token failes with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, 403),

  # Developer with developer API key scoped to correct Run Environment, explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, 200),

  # Developer with developer API key scoped to different Run Environment gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, 404),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, 404),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_IN_WRONG_GROUP, 404),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, 401),
])
def test_run_environment_update_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        send_uuid_type: str, status_code: int,
        user_factory, group_factory, run_environment_factory, api_client) -> None:
    """
    This only tests access control to the PATCH endpoint, not the actual changes.
    """

    user = user_factory()

    run_environment, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=send_uuid_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            api_client=api_client)

    response = client.patch(url, {})

    assert response.status_code == status_code

    run_environment.refresh_from_db()

    if status_code == 200:
        assert group_access_level is not None

        ensure_serialized_run_environment_valid(
                response_re=cast(dict[str, Any], response.data),
                run_environment=run_environment, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_post, api_key_access_level, api_key_scope_type,
  alert_method_send_type,
  status_code, validation_error_attribute
""", [
  # POST - Developer authenticated with JWT succeeds with no Run Environment
  # where Alert Method is also unscoped
  (True, None, None,
   SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   201, None),
  # PUT - Developer authenticated with JWT succeeds with no Run Environment
  # where Alert Method is also unscoped
  (False, None, None,
   SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   200, None),
  # PUT - Developer authenticated with JWT succeeds with a specific Run Environment
  # where Alert Method is scoped correctly
  (False, None, None,
   SEND_ID_CORRECT,
   200, None),
  # POST - Developer authenticated with JWT fails
  # where Alert Method is scoped to a different Run Environment
  (True, None, None,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'default_alert_methods'),
  # PUT - Developer authenticated with JWT succeeds
  # where Alert Method is scoped to a different Run Environment
  (False, None, None,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'default_alert_methods'),
  # POST - Developer with unscoped API Key succeeds
  # where Alert Method is also unscoped
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   201, None),
  # PUT - Developer with unscoped API Key succeeds
  # where Alert Method is also unscoped
  (False, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   200, None),
  # PUT - Developer with scoped API Key succeeds with no explicit Run Environment
  # and an Alert Method that scoped to the API Key's Run Environment
  (False, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT,
   200, None),
  # PUT - Developer with scoped API Key fails using with no explicit Run Environment
  # Alert Method with different Run Environment
  (False, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_WITH_OTHER_RUN_ENVIRONMENT,
   422, 'default_alert_methods'),
  # PUT - Developer with scoped API Key fails using matching Run Environment
  # but unscoped Alert Method
  (False, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_WITHOUT_RUN_ENVIRONMENT,
   200, None),
])
def test_run_environment_set_alert_methods(is_post: bool,
        api_key_access_level: Optional[int], api_key_scope_type: str,
        alert_method_send_type: Optional[str],
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        alert_method_factory,
        api_client) -> None:
    """
    Tests for setting method details.
    """
    group_access_level = UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER

    user = user_factory()

    uuid_send_type = SEND_ID_NONE if is_post else SEND_ID_CORRECT

    run_environment, api_key_run_environment, client, url = common_setup(
            is_authenticated=True,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            api_client=api_client)

    # Prevent conflict with previous iteration's created entity
    request_data: dict[str, Any] = {
      'name': f'Some RE with POST {is_post}'
    }

    am_group = user.groups.first()
    am_run_environment: Optional[RunEnvironment] = None
    if alert_method_send_type == SEND_ID_CORRECT:
        am_run_environment = run_environment
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

    print(f"am_run_environment = {am_run_environment}, alert_method = {alert_method}")

    if alert_method_send_type:
        am_uuid = alert_method.uuid
        if alert_method_send_type == SEND_ID_NOT_FOUND:
            am_uuid = uuid.uuid4()

        body_alert_methods = [{
            'uuid': str(am_uuid)
        }]

        request_data['default_alert_methods'] = body_alert_methods

    old_count = RunEnvironment.objects.count()

    print(f"request data = {request_data}")

    if is_post:
        response = client.post(url, data=request_data)
    else:
        response = client.patch(url, data=request_data)

    new_count = RunEnvironment.objects.count()

    expected_status_code = status_code

    assert response.status_code == expected_status_code

    if (status_code >= 200) and (status_code < 300):
        if is_post:
            assert new_count == old_count + 1
        else:
            assert new_count == old_count

        response_re = cast(dict[str, Any], response.data)
        re_uuid = response_re['uuid']
        run_environment = RunEnvironment.objects.get(uuid=re_uuid)

        assert group_access_level is not None
        ensure_serialized_run_environment_valid(response_re=response_re,
                run_environment=run_environment,
                user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level,
                api_key_run_environment=api_key_run_environment)

        print(f"response = {response_re}")

        assert(response_re['default_alert_methods'][0]['uuid'] == str(alert_method.uuid))
    else:
        assert new_count == old_count
        check_validation_error(response, validation_error_attribute)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  send_uuid_type, status_code
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_CORRECT, 204),

  # Developer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, 204),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, 403),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, 403),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, 204),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, 204),

  # Observer with JWT token failes with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, 403),

  # Developer with developer API key scoped to correct Run Environment, explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, 204),

  # Developer with developer API key scoped to different Run Environment gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_OTHER,
   SEND_ID_CORRECT, 404),

  # Admin with API Key, wrong UUID gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_NOT_FOUND, 404),

  # Admin with API Key with wrong group gets 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_IN_WRONG_GROUP, 404),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_CORRECT, 401),
])
def test_run_environment_delete(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        send_uuid_type: str, status_code: int,
        user_factory, group_factory, run_environment_factory, api_client) -> None:
    user = user_factory()

    run_environment, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=send_uuid_type,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            api_client=api_client)

    response = client.delete(url)

    assert response.status_code == status_code

    exists = RunEnvironment.objects.filter(pk=run_environment.pk).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists
