from typing import Any, Dict, List, Optional, Tuple, cast

import uuid
from urllib.parse import quote

from django.contrib.auth.models import User

from processes.models import (
  EmailNotificationProfile, RunEnvironment, UserGroupAccessLevel
)

from processes.serializers import EmailNotificationProfileSerializer

import pytest

from rest_framework.test import APIClient

from conftest import *

def ensure_serialized_email_notification_profile_valid(response_entity: Dict[str, Any],
        email_notification_profile: EmailNotificationProfile, user: User,
        group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> None:
    context = context_with_authenticated_request(user=user,
            group=email_notification_profile.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    assert response_entity == EmailNotificationProfileSerializer(email_notification_profile,
            context=context).data

    if api_key_run_environment:
        assert(response_entity['run_environment']['uuid'] == \
                str(api_key_run_environment.uuid))

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
def test_email_notification_profile_list(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        user_has_another_group: bool, send_group_id_type: str,
        status_code: int, expected_indices: List[int],
        user_factory, group_factory, run_environment_factory,
        email_notification_profile_factory, api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    another_group = group_factory()

    if user_has_another_group:
        set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    am_group = group

    production_run_environment = run_environment_factory(created_by_group=group)
    test_run_environment = run_environment_factory(created_by_group=group)

    email_notification_profiles = [
      email_notification_profile_factory(name='Production',
              created_by_group=am_group,
              run_environment=production_run_environment),
      email_notification_profile_factory(name='Scopeless',
              created_by_group=am_group,
              run_environment=None),
      email_notification_profile_factory(name='Test',
              created_by_group=am_group,
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

    response = client.get('/api/v1/email_notification_profiles/', params)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        page = response.data
        assert page['count'] == len(expected_indices)
        results = page['results']

        for i in expected_indices:
            response_entity = results[i]
            target_am = email_notification_profiles[expected_indices[i]]
            ensure_serialized_email_notification_profile_valid(response_entity,
                    email_notification_profile=target_am, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=api_key_run_environment)


def common_setup(is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str, existing_has_run_environment: bool,
        user, group_factory, run_environment_factory, email_notification_profile_factory, api_client) \
        -> Tuple[EmailNotificationProfile, Optional[RunEnvironment], APIClient, str]:
    group = user.groups.first()

    if group_access_level is not None:
        set_group_access_level(user=user, group=group,
                access_level=group_access_level)

    am_group = group

    run_environment = run_environment_factory(created_by_group=am_group)
    another_run_environment = run_environment_factory(created_by_group=am_group)

    enp_run_environment = run_environment if existing_has_run_environment else None

    email_notification_profile = email_notification_profile_factory(created_by_group=am_group,
      run_environment=enp_run_environment)

    api_key_run_environment = None
    if api_key_scope_type == SCOPE_TYPE_CORRECT:
        api_key_run_environment = run_environment
    elif api_key_scope_type == SCOPE_TYPE_OTHER:
        api_key_run_environment = another_run_environment

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    url = '/api/v1/email_notification_profiles/'

    if uuid_send_type != SEND_ID_NONE:
        entity_uuid = uuid.uuid4()
        if uuid_send_type == SEND_ID_CORRECT:
            entity_uuid = email_notification_profile.uuid
        elif uuid_send_type == SEND_ID_IN_WRONG_GROUP:
            another_group = group_factory()
            set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
            email_notification_profile_in_other_group = email_notification_profile_factory(
                    created_by_group=another_group)
            entity_uuid = email_notification_profile_in_other_group.uuid

        url += quote(str(entity_uuid)) + '/'

    return (email_notification_profile, api_key_run_environment, client, url)

def make_request_body(uuid_send_type: Optional[str],
        run_environment_send_type: Optional[str],
        user: User,
        api_key_run_environment: Optional[RunEnvironment],
        email_notification_profile: EmailNotificationProfile,
        group_factory, run_environment_factory) -> Dict[str, Any]:

    request_data: Dict[str, Any] = {
      'name': 'Some ENP',
      'subject_template': 'Hey!',
      'body_template': 'Something is wrong!',
      'to_addresses': ['agh@asdf.com']
    }

    if uuid_send_type == SEND_ID_NOT_FOUND:
        request_data['uuid'] = str(uuid.uuid4())
    elif uuid_send_type == SEND_ID_WRONG:
        request_data['uuid'] = str(email_notification_profile.uuid)

    if run_environment_send_type == SEND_ID_CORRECT:
        assert api_key_run_environment is not None
        request_data['run_environment'] = {
          'uuid': str(api_key_run_environment.uuid)
        }
    elif run_environment_send_type == SEND_ID_OTHER:
        another_run_environment = run_environment_factory(created_by_group=user.groups.first())
        request_data['run_environment'] = {
          'uuid': str(another_run_environment.uuid)
        }
    elif run_environment_send_type == SEND_ID_IN_WRONG_GROUP:
        group = group_factory()
        set_group_access_level(user=user, group=group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

        another_run_environment = run_environment_factory(created_by_group=group)
        request_data['run_environment'] = {
          'uuid': str(another_run_environment.uuid)
        }
    elif run_environment_send_type == SEND_ID_NONE:
        request_data['run_environment'] = None

    return request_data


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
def test_email_notification_profile_fetch(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        api_key_scope_type: str,
        uuid_send_type: str, existing_has_run_environment: bool,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        email_notification_profile_factory, api_client) -> None:
    user = user_factory()
    email_notification_profile, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            existing_has_run_environment=existing_has_run_environment,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            email_notification_profile_factory=email_notification_profile_factory,
            api_client=api_client)

    response = client.get(url)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        ensure_serialized_email_notification_profile_valid(response_entity=response.data,
          email_notification_profile=email_notification_profile, user=user,
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
   SEND_ID_NONE, SEND_ID_NONE,
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
   SEND_ID_NONE, SEND_ID_OTHER,
   201, None),

  # Developer with unscoped API Key succeeds when Run Environment is not specified
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_NONE, None,
   201, None),

  # uuid of existing Profile is present in request body
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_WRONG, SEND_ID_NONE,
   400, 'uuid'),

   # Developer with unscoped API Key cannot attach a Run Environment in the
   # wrong Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_NONE,
   SEND_ID_NONE, SEND_ID_IN_WRONG_GROUP,
   422, 'run_environment'),

   # Developer with scoped API Key succeeds when Profile is scoped
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

   # Developer with scoped API Key cannot update Profile with no
   # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_NONE,
   403, None),

   # Developer with scoped API Key cannot create Profile with a different
   # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_NONE, SEND_ID_OTHER,
   422, 'run_environment'),

  # Support user with API Key fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_NONE, SEND_ID_NONE,
   403, None),

  # Admin with API Key with support access fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_NONE, SEND_ID_NONE,
   403, None),

  # Admin with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_NONE, SEND_ID_NONE,
   201, None),

  # Developer with JWT token succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_NONE, SEND_ID_NONE,
   201, None),

  # Observer with JWT token fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_NONE, SEND_ID_NONE,
   403, None),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   SEND_ID_NONE, SEND_ID_NONE,
   401, None),
])
def test_email_notification_profile_create_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        body_uuid_type: str, run_environment_send_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        email_notification_profile_factory,
        api_client) -> None:
    """
    This only tests access control to the CREATE endpoint, not the actual changes.
    """

    user = user_factory()

    email_notification_profile, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=SEND_ID_NONE,
            existing_has_run_environment=False,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            email_notification_profile_factory=email_notification_profile_factory,
            api_client=api_client)

    old_count = EmailNotificationProfile.objects.count()

    request_data = make_request_body(uuid_send_type=body_uuid_type,
            run_environment_send_type=run_environment_send_type,
            user=user,
            group_factory=group_factory,
            api_key_run_environment=api_key_run_environment,
            email_notification_profile=email_notification_profile,
            run_environment_factory=run_environment_factory)

    response = client.post(url, data=request_data)

    assert response.status_code == status_code

    new_count = EmailNotificationProfile.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1

        response_entity = cast(Dict[str, Any], response.data)
        entity_uuid = response_entity['uuid']
        created_am = EmailNotificationProfile.objects.get(uuid=entity_uuid)

        assert group_access_level is not None
        ensure_serialized_email_notification_profile_valid(response_entity=response_entity,
          email_notification_profile=created_am, user=user,
          group_access_level=group_access_level,
          api_key_access_level=api_key_access_level,
          api_key_run_environment=api_key_run_environment)
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
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   SEND_ID_CORRECT, None,
   None, True,
   200, None),

  # Developer with unscoped API Key succeeds when UUID in body matches
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_CORRECT,
   SEND_ID_NONE, True,
   200, None),

  # Developer with unscoped API Key fails when UUID in body does not match
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_OTHER,
   SEND_ID_NONE, True,
   200, None),

  # Developer with unscoped API Key fails when UUID in body is not found
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, SEND_ID_WRONG,
   SEND_ID_NONE, True,
   200, None),

  # Developer with unscoped API Key succeeds in unscoping Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None,
   SEND_ID_CORRECT, None,
   SEND_ID_NONE, True,
   200, None),

  # Developer with unscoped API Key succeeds in updating unscoped Profile
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

  # Support user with API Key fails with 403 on scoped Profile
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, None,
   SEND_ID_CORRECT, None,
   None, True,
   403, None),

  # Support user with JWT token fails with 403 on unscoped Profile
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, None,
   None, False,
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

  # Support user with JWT token fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, None,
   None, True,
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
  # when specifying an empty Run Environment
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
def test_email_notification_profile_update_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        request_uuid_send_type: str, body_uuid_send_type: Optional[str],
        run_environment_send_type: str, existing_has_run_environment: bool,
        status_code: int, validation_error_attribute: Optional[str],
        user_factory, group_factory, run_environment_factory,
        email_notification_profile_factory,
        api_client) -> None:
    """
    This only tests access control to the PATCH endpoint, not the actual changes.
    """

    user = user_factory()

    email_notification_profile, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=request_uuid_send_type,
            existing_has_run_environment=existing_has_run_environment,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            email_notification_profile_factory=email_notification_profile_factory,
            api_client=api_client)

    request_data = make_request_body(uuid_send_type=body_uuid_send_type,
            run_environment_send_type=run_environment_send_type,
            user=user,
            api_key_run_environment=api_key_run_environment,
            email_notification_profile=email_notification_profile,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory)

    old_count = EmailNotificationProfile.objects.count()

    response = client.patch(url, request_data)

    assert response.status_code == status_code
    assert EmailNotificationProfile.objects.count() == old_count

    email_notification_profile.refresh_from_db()

    if status_code == 200:
        assert group_access_level is not None

        ensure_serialized_email_notification_profile_valid(response_entity=response.data,
          email_notification_profile=email_notification_profile, user=user,
          group_access_level=group_access_level,
          api_key_access_level=api_key_access_level,
          api_key_run_environment=api_key_run_environment)
    else:
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

  # Developer with unscoped API Key can deleted unscoped Profile
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

  # Developer with JWT token succeeds deleting Profile scoped to
  # Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, True,
   204),

  # Developer with JWT token succeeds deleting unscoped Profile
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   SEND_ID_CORRECT, False,
   204),

  # Support user with JWT token fails with 403
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   None, None,
   SEND_ID_CORRECT, True,
   403),

  # Developer with developer API key scoped to correct Run Environment, explicit group finds the desired one
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, True,
   204),

  # Developer with developer API key scoped to Run Environment
  # cannot delete unscoped Profile
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, SCOPE_TYPE_CORRECT,
   SEND_ID_CORRECT, False,
   404),

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
def test_email_notification_profile_delete(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        uuid_send_type: str, existing_has_run_environment: bool,
        status_code: int,
        user_factory, group_factory, run_environment_factory,
        email_notification_profile_factory, api_client) -> None:
    user = user_factory()

    email_notification_profile, api_key_run_environment, client, url = common_setup(
            is_authenticated=is_authenticated,
            group_access_level=group_access_level,
            api_key_access_level=api_key_access_level,
            api_key_scope_type=api_key_scope_type,
            uuid_send_type=uuid_send_type,
            existing_has_run_environment=existing_has_run_environment,
            user=user,
            group_factory=group_factory,
            run_environment_factory=run_environment_factory,
            email_notification_profile_factory=email_notification_profile_factory,
            api_client=api_client)

    response = client.delete(url)

    assert response.status_code == status_code

    exists = EmailNotificationProfile.objects.filter(pk=email_notification_profile.pk).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists
