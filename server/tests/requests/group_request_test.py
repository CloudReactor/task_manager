from typing import Optional

from django.contrib.auth.models import Group

from processes.common.request_helpers import context_with_request
from processes.models import (
    SaasToken, UserGroupAccessLevel
)
from processes.serializers import GroupSerializer

import pytest

from conftest import *

@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      status_code, expected_group_count
""", [
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False, 200, 2),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False, 200, 2),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False, 200, 2),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, False, 200, 2),

  # User is only member of 1 group
  (True, None, False, 200, 1),

  # Not authenticated user gets a 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False, 401, 0),

  # API Key not allowed to be used for access
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True, 401, 0),
])
def test_group_list(is_authenticated: bool,
        group_access_level: Optional[int], use_api_key: bool,
        status_code: int, expected_group_count: int,
        user_factory, group_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    assert group is not None

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    another_group_of_user = group_factory()
    set_group_access_level(user=user, group=another_group_of_user,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER)

    group_user_is_not_member_of = group_factory()

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    response = client.get('/api/v1/groups/')

    assert response.status_code == status_code

    if status_code == 200:
        page = response.data
        assert page['count'] == expected_group_count
        context = context_with_request()

        for response_group in page['results']:
            name = response_group['name']

            if name == group.name:
                assert expected_group_count > 1
                assert response_group == GroupSerializer(
                        group, context=context).data
                found_group = True
            else:
                assert response_group == GroupSerializer(
                        another_group_of_user, context=context).data
                found_another_group = True

        if expected_group_count > 1:
            assert found_group

        assert found_another_group

@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      send_id_type, status_code
""", [
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, 200),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   SEND_ID_CORRECT, 200),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, False,
   SEND_ID_CORRECT, 200),
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, False,
   SEND_ID_CORRECT, 200),

  # User is not a member of the group
  (True, None, False,
   SEND_ID_CORRECT, 404),

  # Not authenticated user gets a 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, 401),

  # API Key not allowed to be used for access
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
   SEND_ID_CORRECT, 401),
])
def test_group_fetch(is_authenticated: bool,
        group_access_level: Optional[int], use_api_key: bool,
        send_id_type: str, status_code: int,
        user_factory, group_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    assert group is not None

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    group_id = group.id
    if send_id_type == SEND_ID_NOT_FOUND:
        group_id = 9231610

    response = client.get(f'/api/v1/groups/{group_id}/')

    assert response.status_code == status_code

    if status_code == 200:
        assert response.data == GroupSerializer(
                group, context=context_with_request()).data


@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      is_group_existing, is_name_conflict, status_code
""", [
  # Admin can update group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, False, 200),

  # Developer not allowed to update group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   True, False, 403),

  # API key not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
   True, False, 401),

  # Non-member of Group cannot update Group
  (True, None, False,
   True, False, 404),

  # Not Authenticated
  (False, None, False,
   True, False, 401),

  # Name conflict
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   True, True, 409),
])
def test_group_update(is_authenticated: bool,
        group_access_level: Optional[int], use_api_key: bool,
        is_group_existing: bool, is_name_conflict: bool, status_code: int,
        user_factory, api_client):
    user = user_factory()
    group = user.groups.first()
    old_group_name = group.name

    assert group is not None

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    if is_name_conflict:
        Group(name='Renamed').save()

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    group_id = group.pk

    if not is_group_existing:
        group_id = 192399213

    response = client.patch(f'/api/v1/groups/{group_id}/', {
        'name': 'Renamed',
    })

    assert response.status_code == status_code

    group.refresh_from_db()

    if status_code == 200:
        assert group.name == 'Renamed'
        context = context_with_request()
        assert response.data == GroupSerializer(group, context=context).data
    else:
        assert group.name == old_group_name

@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, use_api_key, is_name_conflict, status_code
""", [
  # Happy path
  (True, False, False, 201),

  # Not authenticated
  (False, False, False, 401),

  # API key not allowed
  (True, True, False, 401),

  # Name conflict
  (True, False, True, 409),
])
def test_group_creation(is_authenticated: bool, use_api_key: bool,
        is_name_conflict: bool,
        status_code: int, user_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    existing_group = None
    if is_name_conflict:
        existing_group = Group(name='Another Group')
        existing_group.save()

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    response = client.post('/api/v1/groups/', {
        'name': 'Another Group'
    })

    assert response.status_code == status_code

    fetched_group = Group.objects.filter(name='Another Group').first()
    if status_code == 201:
        assert fetched_group is not None
    elif is_name_conflict:
        assert fetched_group is not None # for mypy
        assert fetched_group == existing_group
        assert user not in fetched_group.user_set.all()
    else:
        assert fetched_group is None


@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, api_key_access_level, is_group_existing, status_code
""", [
  # Happy path
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None, True, 204),

  # Admin access is required
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, None, True, 403),

  # API key not allowed for this operation
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True, 401),

  # Not authenticated
  (False, None, None, True, 401),

  # Can't find existing group by ID
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None, False, 404),
])
def test_group_removal(is_authenticated: bool,
        group_access_level: Optional[int],
        api_key_access_level: Optional[int], is_group_existing: bool,
        status_code: int, user_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    assert group is not None

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    group_id = group.pk

    if not is_group_existing:
        group_id = 192399213

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    response = client.delete(f'/api/v1/groups/{group_id}/')

    assert response.status_code == status_code

    found_groups = Group.objects.filter(pk=group.pk)

    if status_code == 204:
        assert not found_groups.exists()
    else:
        assert found_groups.exists()
