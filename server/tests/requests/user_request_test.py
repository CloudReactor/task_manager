from typing import Any, List, Optional, cast

from urllib.parse import quote

from django.contrib.auth.models import Group

from processes.common.request_helpers import context_with_request
from processes.models import (
    UserGroupAccessLevel
)

from processes.serializers import SaasTokenSerializer, UserSerializer

import pytest

from conftest import *

def make_test_username(send_username_type: str,
    user: User, group: Group, user_factory) -> str:
    username = user.username

    if send_username_type == SEND_ID_NOT_FOUND:
        username = 'blahblah'
    elif send_username_type == SEND_ID_IN_WRONG_GROUP:
        another_user = user_factory()
        username = another_user.username
    elif send_username_type == SEND_ID_WRONG:
        another_user = user_factory()
        username = another_user.username
        set_group_access_level(user=another_user, group=group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT)

    return username

@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level, use_api_key,
  user_has_another_group, send_group_id_type, status_code
""", [
  # Happy path for admin user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   False, SEND_ID_NONE, 200),

  # Happy path for support user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   False, SEND_ID_NONE, 200),

  # Support access level is required
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK, False,
   False, SEND_ID_NONE, 403),

  # Sending correct group ID is fine
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   False, SEND_ID_CORRECT, 200),

  # User with multiple groups needs to specify group ID
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, SEND_ID_NONE, 400),

  # User with multiple groups needs to specify group ID
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, SEND_ID_CORRECT, 200),

  # User with multiple groups with bad group ID
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, SEND_ID_NOT_FOUND, 400),

  # Anonymous user gets 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   False, SEND_ID_CORRECT, 401),

  # Authentication via API key gets 401
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
   False, SEND_ID_CORRECT, 401),

  # TODO: check filtering, ordering
])
def test_user_list(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
        user_has_another_group: bool, send_group_id_type: str,
        status_code: int,
        user_factory, group_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    another_group = group_factory()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    if user_has_another_group:
        yet_another_group = group_factory()
        yet_another_group.user_set.add(user)

    observer = user_factory()
    set_group_access_level(user=observer, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER)

    dev = user_factory()
    set_group_access_level(user=dev, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    user_in_another_group = user_factory()

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    params = {}

    if send_group_id_type == SEND_ID_CORRECT:
        params['group__id'] = str(group.id)
    elif send_group_id_type == SEND_ID_NOT_FOUND:
        params['group__id'] = '666'

    response = client.get('/api/v1/users/', params)

    assert response.status_code == status_code

    if status_code == 200:
        page = response.data
        assert page['count'] == 3
        results = page['results']
        context = context_with_request()

        def ensure_user_included(expected_user):
            body_user = list(filter(
                    lambda user: user['username'] == expected_user.username,
                    results))[0]
            assert body_user == UserSerializer(
                    expected_user, context=context).data

        ensure_user_included(user)
        ensure_user_included(observer)
        ensure_user_included(dev)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level, use_api_key,
  send_username_type, status_code
""", [
  # Happy path for admin user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, 200),

  # Happy path for support user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_CORRECT, 200),

  # Anonymous user gets 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, 401),

  # Authentication via API key gets 401
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
   SEND_ID_CORRECT, 401),

  # Request for other user is allowed by support user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_WRONG, 200),

  # Request for user in another group is not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_IN_WRONG_GROUP, 404),

  # Request for non-existent user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_NOT_FOUND, 404),
])
def test_user_fetch(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
        send_username_type: str,
        status_code: int,
        user_factory, group_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    another_group = group_factory()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    username = make_test_username(send_username_type=send_username_type,
            user=user, group=group, user_factory=user_factory)

    response = client.get('/api/v1/users/' + quote(username) + '/')

    assert response.status_code == status_code

    if status_code == 200:
        expected_user = user

        if send_username_type == SEND_ID_WRONG:
            expected_user = User.objects.get(username=username)

        assert response.data == UserSerializer(expected_user,
                context=context_with_request()).data


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level, use_api_key, status_code,
""", [
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False, 405),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False, 405),
  (True, None, False, 405),
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False, 401),
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True, 401),
])
def test_user_creation(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
        status_code: int, user_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    request_body = {
      'username': 'arr@pirate.com',
      'password': 'Nota78347BAADPAss',
      'email': 'arr@pirate.com',
    }

    response = client.post('/api/v1/users/', request_body)
    assert response.status_code == status_code


CHANGED_VALUES = {
    'first_name': 'Zelena',
    'last_name': 'Martes',
    'username': 'changed@foo.com',
    'password':  'Nota78347BAADPAss',
    'email': 'agoodemail@goo.com'
}

UPDATABLE_ATTRIBUTES = ['first_name', 'last_name']

@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level, use_api_key,
  send_username_type, fields_to_change, value_overrides, status_code
""", [
  # Happy path for support user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_CORRECT, ['*'], {}, 200),

  # User cannot change username (handled by djsoer)
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_CORRECT, ['username'], {}, 400),

  # User cannot change username to an existing username (handled by djsoer)
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_CORRECT, ['username'], {'username': 'existing@stuff.com'}, 400),

  # User cannot change password (handled by djsoer)
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_CORRECT, ['password'], {}, 400),

  # User cannot change password to weak one (handled by djsoer)
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_CORRECT, ['password'], {'password': 'pw'}, 400),

  # User cannot change email (handled by djsoer)
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   SEND_ID_CORRECT, ['email'], {}, 400),

  # Anonymous user gets 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, ['last_name'], {}, 401),

  # Authentication via API key gets 401
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
   SEND_ID_CORRECT, ['last_name'], {}, 401),

  # Can't update another user in the group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_WRONG, ['first_name'], {}, 403),

  # Can't update another user in the group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_IN_WRONG_GROUP, ['first_name'], {}, 404),

  # Can't update a non-existent user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_NOT_FOUND, ['first_name'], {}, 404),
])
def test_user_update(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
        send_username_type, fields_to_change: List[str],
        value_overrides: dict[str, Any],
        status_code: int,
        user_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    username = make_test_username(send_username_type=send_username_type,
            user=user, group=group, user_factory=user_factory)

    existing_user = user_factory(username='existing@stuff.com')
    existing_user.save()

    request_body = {}

    change_all = CHANGE_ALL in fields_to_change

    if change_all:
        fields_to_change = list(set(CHANGED_VALUES.keys()) \
                .intersection(UPDATABLE_ATTRIBUTES))

    old_field_values = {}

    for field in fields_to_change:
          old_field_values[field] = user.__dict__[field]
          request_body[field] = value_overrides.get(field,
                  CHANGED_VALUES.get(field))

    response = client.patch('/api/v1/users/' +
        quote(username) + '/', request_body)

    assert response.status_code == status_code

    user.refresh_from_db()
    response_user = cast(dict[str, Any], response.data)
    if status_code == 200:
        for field in fields_to_change:
            v =  value_overrides.get(field,
              CHANGED_VALUES.get(field))
            assert user.__dict__[field] == v
            assert response_user[field] == v

        assert response_user == UserSerializer(user,
                context=context_with_request()).data
    else:
        for field in old_field_values:
            assert user.__dict__[field] == old_field_values[field]


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level, use_api_key,
  send_username_type, status_code
""", [
  # Happy path for support user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_CORRECT, 204),

  # Anonymous user gets 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, 401),

  # Authentication via API key gets 401
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
   SEND_ID_CORRECT, 401),

  # Can't delete another user in the group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_WRONG, 403),

  # Can't delete another user in the group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_IN_WRONG_GROUP, 404),

  # Can't update a non-existent user
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_NOT_FOUND, 404),
])
def test_user_removal(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
        send_username_type, status_code: int,
        user_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    username = make_test_username(send_username_type=send_username_type,
        user=user, group=group, user_factory=user_factory)

    response = client.delete('/api/v1/users/' +
        quote(username) + '/')

    assert response.status_code == status_code

    exists = User.objects.filter(username=user.username).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists
