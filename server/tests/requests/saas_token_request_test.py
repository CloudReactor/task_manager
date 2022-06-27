from typing import Any, Dict, Optional

import uuid
from urllib.parse import quote

from django.utils import timezone
from django.contrib.auth.models import Group

from processes.common.request_helpers import (
  context_with_request
)

from processes.models import (
  RunEnvironment, SaasToken, Subscription, UserGroupAccessLevel
)

from processes.serializers import SaasTokenSerializer

import pytest

from conftest import *

RUN_ENVIRONMENT_TYPE_EXISTING = 'existing'
RUN_ENVIRONMENT_TYPE_BLANK = 'blank'
RUN_ENVIRONMENT_TYPE_NOT_FOUND = 'not_found'
RUN_ENVIRONMENT_TYPE_NOT_IN_GROUP = 'not_in_group'

def set_run_environment_in_request(request_body: Dict[str, Any],
        use_run_environment_type: str,
        existing_run_environment: Optional[RunEnvironment],
        run_environment_factory) -> Optional[RunEnvironment]:
    run_environment_uuid = None
    run_environment = None
    if use_run_environment_type == RUN_ENVIRONMENT_TYPE_NOT_FOUND:
        run_environment_uuid = uuid.uuid4()
    elif use_run_environment_type == RUN_ENVIRONMENT_TYPE_NOT_IN_GROUP:
        run_environment = run_environment_factory()
        run_environment_uuid = run_environment.uuid
    elif use_run_environment_type == RUN_ENVIRONMENT_TYPE_EXISTING:
        run_environment = existing_run_environment
        assert run_environment is not None
        run_environment_uuid = run_environment.uuid

    if run_environment_uuid:
        request_body['run_environment'] = {
          'uuid': str(run_environment_uuid)
        }

    return run_environment


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level, use_api_key,
  user_has_another_group, send_group_id_type, status_code, expected_token_count
""", [
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   False, SEND_ID_NONE, 200, 3),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   False, SEND_ID_NONE, 200, 2),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   False, SEND_ID_NONE, 403, 0),

  # Sending correct group ID is fine
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   False, SEND_ID_CORRECT, 200, 3),

  # User with multiple groups needs to specify group ID
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, SEND_ID_NONE, 400, 0),

  # User with multiple groups needs to specify group ID
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, SEND_ID_CORRECT, 200, 2),

  # User with multiple groups with bad group ID
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, SEND_ID_NOT_FOUND, 400, 0),

  # Anonymous user gets 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   False, SEND_ID_CORRECT, 401, 3),

  # Authentication via API key gets 401
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
   False, SEND_ID_CORRECT, 401, 3),

  # TODO: check filtering, ordering
])
def test_saas_token_list(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
        user_has_another_group: bool, send_group_id_type: str,
        status_code: int, expected_token_count: int,
        user_factory, group_factory, run_environment_factory, api_client):
    user = user_factory()
    another_group = group_factory()

    if group_access_level is None:
        group = another_group
    else:
        group = user.groups.first()
        ugal = UserGroupAccessLevel.objects.get(user=user, group=group)
        ugal.access_level = group_access_level
        ugal.save()

    if user_has_another_group:
        yet_another_group = group_factory()
        yet_another_group.user_set.add(user)

    admin_token = SaasToken(user=user_factory(), group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
    admin_token.save()

    dev_token = SaasToken(user=user_factory(), group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)
    dev_token.save()

    task_token = SaasToken(user=user_factory(), group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK)
    task_token.save()

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    params = {}

    if send_group_id_type == SEND_ID_CORRECT:
        params['group__id'] = str(group.id)
    elif send_group_id_type == SEND_ID_NOT_FOUND:
        params['group__id'] = '666'

    response = client.get('/api/v1/api_keys/', params)

    assert response.status_code == status_code

    if status_code == 200:
        page = response.data
        assert page['count'] == expected_token_count
        results = page['results']
        context = context_with_request()

        def ensure_token_included(expected_token):
            body_token = list(filter(
                    lambda token: token['access_level'] == expected_token.access_level,
                    results))[0]
            assert body_token == SaasTokenSerializer(expected_token,
                    context=context).data

        if expected_token_count > 2:
            ensure_token_included(admin_token)

        if expected_token_count > 1:
            ensure_token_included(dev_token)

        if expected_token_count > 0:
            ensure_token_included(task_token)

@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level, use_api_key,
  send_uuid_type, existing_token_access_level, status_code
""", [
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, 200),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, 200),

  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   SEND_ID_CORRECT, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, 200),

  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   SEND_ID_CORRECT, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, 200),

  # Tokens with higher access level than the user are not visible
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   SEND_ID_CORRECT, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, 404),

  # Developer access is required
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_CORRECT, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, 404),

  # Not found token
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_NOT_FOUND, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, 404),

  # Token not in user's group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_IN_WRONG_GROUP, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, 404),

  # User with no access to the group gets a 404
  (True, None, False,
   SEND_ID_CORRECT, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, 404),

  # Anonymous user gets 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, 401),

  # Authentication via API key gets 401
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
   SEND_ID_CORRECT, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, 401),
])
def test_saas_token_fetch(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
        send_uuid_type: str, existing_token_access_level: Optional[int],
        status_code: int,
        user_factory, group_factory, run_environment_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    token = None

    if existing_token_access_level is not None:
        token_group = group

        if send_uuid_type == SEND_ID_IN_WRONG_GROUP:
            token_group = group_factory()

        token = SaasToken(user=user, group=token_group,
                access_level=existing_token_access_level)
        token.save()

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    token_uuid = uuid.uuid4()
    if send_uuid_type == SEND_ID_CORRECT:
        assert token is not None
        token_uuid = token.uuid

    response = client.get(f'/api/v1/api_keys/{quote(str(token_uuid))}/')

    assert response.status_code == status_code

    if status_code == 200:
        assert token is not None
        assert response.data == SaasTokenSerializer(token,
                context=context_with_request()).data


@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      name, requested_access_level, use_run_environment_type,
      enabled, existing_token_count,
      status_code
""", [
  # Happy path for admin
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, RUN_ENVIRONMENT_TYPE_EXISTING,
   True, 1,
   201),
  # Not authenticated
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, RUN_ENVIRONMENT_TYPE_EXISTING,
   True, 1,
   401),
  # Happy path for developer
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, RUN_ENVIRONMENT_TYPE_EXISTING,
   True, 1,
   201),
  # Developer allocates token with less access
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, RUN_ENVIRONMENT_TYPE_EXISTING,
   True, 1,
   201),
  # Privilege escalation
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, RUN_ENVIRONMENT_TYPE_EXISTING,
   True, 1,
   403),
  # User access level has insufficient privilege
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, RUN_ENVIRONMENT_TYPE_EXISTING,
   True, 1,
   403),
  # API key used
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, RUN_ENVIRONMENT_TYPE_EXISTING,
   True, 1,
   401),
  # Duplicate name
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Existing Token', UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, RUN_ENVIRONMENT_TYPE_EXISTING,
   True, 1,
   201),
  # Run Environment is omitted
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, RUN_ENVIRONMENT_TYPE_BLANK,
   True, 1,
   201),
  # Run Environment is not found
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, RUN_ENVIRONMENT_TYPE_NOT_FOUND,
   True, 1,
   422),
  # Run Environment is not in the Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, RUN_ENVIRONMENT_TYPE_NOT_IN_GROUP,
   True, 1,
   422),
  # Enabled is omitted
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, RUN_ENVIRONMENT_TYPE_EXISTING,
   False, 1,
   201),
  # Enabled is explicitly False
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, RUN_ENVIRONMENT_TYPE_EXISTING,
   None, 1,
   201),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   'Some Token', UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, RUN_ENVIRONMENT_TYPE_EXISTING,
   None, 5,
   403),
])
def test_saas_token_creation(is_authenticated: bool,
        group_access_level: Optional[int], use_api_key: bool,
        name: Optional[str], requested_access_level: int,
        use_run_environment_type: str, enabled: Optional[bool],
        existing_token_count: int,
        status_code: int, user_factory, run_environment_factory,
        subscription_plan_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    plan = subscription_plan_factory(max_api_keys=5)
    Subscription.objects.create(group=group, subscription_plan=plan,
      active=True, start_at=timezone.now())

    existing_run_environment = RunEnvironment(name='Existing RE',
      created_by_user=user, created_by_group=group)
    existing_run_environment.save()

    existing_token = SaasToken(name='Existing token', user=user, group=group,
        run_environment=existing_run_environment,
        access_level= UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)
    existing_token.save()

    request_body: Dict[str, Any] = {
        'name': name,
    }

    request_body['group'] = {
        'id': group.pk
    }

    if requested_access_level is not None:
        request_body['access_level'] = requested_access_level

    run_environment = set_run_environment_in_request(
            request_body=request_body, use_run_environment_type=use_run_environment_type,
            existing_run_environment=existing_run_environment,
            run_environment_factory=run_environment_factory)

    if enabled is not None:
        request_body['enabled'] = enabled

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    # make_api_client_from_options() may create an API key, so count afterwards
    before_token_count = SaasToken.objects.count()

    for i in range(before_token_count, existing_token_count):
        SaasToken.objects.create(
          run_environment=run_environment,
          user=user,
          group=group,
          access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK
        )

    before_token_count = SaasToken.objects.count()

    response = client.post('/api/v1/api_keys/', request_body)

    assert response.status_code == status_code

    after_token_count = SaasToken.objects.count()
    if status_code == 201:
        assert after_token_count == (before_token_count + 1)

        if enabled is None:
            expected_enabled = True
        else:
            expected_enabled = enabled

        token = SaasToken.objects.filter(name=name, user=user, group=group,
                run_environment=run_environment,
                access_level=requested_access_level,
                enabled=expected_enabled).last()

        assert response.data == SaasTokenSerializer(token,
              context=context_with_request()).data
    else:
        assert after_token_count == before_token_count


@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      is_token_existing, is_token_in_allowed_group,
      has_existing_run_environment,
      is_name_conflict, requested_access_level, use_run_environment_type,
      status_code
""", [
  # Happy path with admin access
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, True,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, RUN_ENVIRONMENT_TYPE_EXISTING,
   200),

  # API key not allowed to be used to authenticate
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
   True, True,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_TASK, RUN_ENVIRONMENT_TYPE_EXISTING,
   401),

  # Happy path with developer access
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, True,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_TASK, RUN_ENVIRONMENT_TYPE_EXISTING,
   200),

  # Insufficient access level (developer required)
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   True, True,
   True,
   False,  UserGroupAccessLevel.ACCESS_LEVEL_TASK, RUN_ENVIRONMENT_TYPE_EXISTING,
   404),

  # Privilege escalation not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, True,
   True,
   False,  UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, RUN_ENVIRONMENT_TYPE_EXISTING,
   403),

  # No access
  (True, None, False,
   True, True,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_TASK, RUN_ENVIRONMENT_TYPE_EXISTING,
   404),

  # Anonymous user not allowed
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, True,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_TASK, RUN_ENVIRONMENT_TYPE_EXISTING,
   401),

  # UUID not found
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   False, True,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_TASK, RUN_ENVIRONMENT_TYPE_EXISTING,
   404),

  # UUID for API key in another Group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, False,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_TASK, RUN_ENVIRONMENT_TYPE_EXISTING,
   404),

  # Name conflict
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, True,
   True,
   True, UserGroupAccessLevel.ACCESS_LEVEL_TASK, RUN_ENVIRONMENT_TYPE_EXISTING,
   200),

  # No explicit access level -- default to TASK
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, True,
   True,
   True, None, RUN_ENVIRONMENT_TYPE_EXISTING,
   200),

  # Add Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, True,
   False,
   False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, RUN_ENVIRONMENT_TYPE_EXISTING,
   200),

  # Remove Run Environment
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, True,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, RUN_ENVIRONMENT_TYPE_BLANK,
   200),

  # Run Environment not found
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, True,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, RUN_ENVIRONMENT_TYPE_NOT_FOUND,
   422),

  # Run Environment not in group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, True,
   True,
   False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, RUN_ENVIRONMENT_TYPE_NOT_IN_GROUP,
   422),
])
def test_saas_token_update(is_authenticated: bool,
        group_access_level: Optional[int], use_api_key: bool,
        is_token_existing: bool, is_token_in_allowed_group: bool,
        has_existing_run_environment: bool,
        is_name_conflict: bool, requested_access_level: Optional[int],
        use_run_environment_type: str,
        status_code: int,
        user_factory, group_factory, run_environment_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    existing_run_environment = RunEnvironment(name='Existing RE',
            created_by_user=user_factory(), created_by_group=group)
    existing_run_environment.save()

    existing_token: Optional[SaasToken] = None
    token_uuid = uuid.uuid4()
    if is_token_existing:
        run_environment = existing_run_environment if has_existing_run_environment else None

        token_group = group
        if not is_token_in_allowed_group:
            token_group = group_factory()

        existing_token = SaasToken(name='Foo', user=user_factory(), group=token_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
                run_environment=run_environment)
        existing_token.save()
        token_uuid = existing_token.uuid

    if is_name_conflict:
        SaasToken(name='Renamed', user=user, group=group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT).save()

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    request_body: Dict[str, Any] = {
        'name': 'Renamed',
    }

    if requested_access_level is not None:
        request_body['access_level'] = requested_access_level

    run_environment = set_run_environment_in_request(
            request_body=request_body, use_run_environment_type=use_run_environment_type,
            existing_run_environment=existing_run_environment,
            run_environment_factory=run_environment_factory)

    response = client.patch(f'/api/v1/api_keys/{quote(str(token_uuid))}/', request_body)

    assert response.status_code == status_code

    if not is_token_existing:
        return

    assert existing_token is not None
    existing_token.refresh_from_db()

    if status_code == 200:
        assert existing_token is not None
        assert existing_token.name == 'Renamed'
        assert existing_token.access_level == requested_access_level or \
                UserGroupAccessLevel.ACCESS_LEVEL_TASK
        assert existing_token.run_environment == run_environment
        context = context_with_request()
        assert response.data == SaasTokenSerializer(existing_token,
                context=context).data
    else:
        assert existing_token.name == 'Foo'


@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      is_token_existing, is_token_in_allowed_group,
      status_code
""", [
  # Happy path with admin access
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, True, 204),

  # Happy path with developer access
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, True, 204),

  # At least developer access is required
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   True, True, 404),

  # Using API key is not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
   True, True, 401),

  # Non-authenticated user is blocked
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, True, 401),

  # Token with the UUID is not found
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, False, 404),

  # Token is not in user's groups
  (True, None, False,
   True, True, 404),

])
def test_saas_token_removal(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: Optional[int],
        is_token_existing: bool, is_token_in_allowed_group: bool,
        status_code: int, user_factory, group_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    assert group is not None

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    existing_token: Optional[SaasToken] = None
    token_uuid = uuid.uuid4()
    if is_token_existing:
        token_group = group
        if not is_token_in_allowed_group:
            token_group = group_factory()

        run_environment = RunEnvironment(name='Existing RE',
            created_by_user=user_factory(), created_by_group=group)
        run_environment.save()

        existing_token = SaasToken(name='Foo', user=user_factory(), group=token_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
                run_environment=run_environment)
        existing_token.save()
        token_uuid = existing_token.uuid

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    response = client.delete(f'/api/v1/api_keys/{quote(str(token_uuid))}/')

    assert response.status_code == status_code

    found_tokens = SaasToken.objects.filter(uuid=token_uuid)

    if status_code == 204:
        assert not found_tokens.exists()
    else:
        assert found_tokens.exists()
