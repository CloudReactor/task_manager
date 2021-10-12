from typing import Any, Dict, Optional

import uuid

from django.contrib.auth.models import Group
from rest_framework import request

from processes.common.request_helpers import context_with_request
from processes.models import UserGroupAccessLevel
from processes.serializers import SaasTokenSerializer

import pytest

from conftest import *

def common_setup(
        is_authenticated: bool, group_access_level: Optional[int],
        use_api_key: Optional[int],
        current_access_level: Optional[int], use_self: bool,
        other_user_access_level: Optional[int],
        user_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    assert group is not None

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    if use_self:
        target_user = user
    else:
        target_user = user_factory()
        set_group_access_level(user=target_user, group=group,
                access_level=current_access_level)

    if other_user_access_level is not None:
        other_user = user_factory()
        set_group_access_level(user=other_user, group=group,
                access_level=other_user_access_level)

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    request_body: Dict[str, Any] = {}

    target_username = target_user.username
    request_body['user'] = { 'username': target_username }
    request_body['group'] = { 'id': group.id }

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    return client, request_body, target_user, group

@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      current_access_level, requested_access_level,
      update_self, other_user_access_level,
      status_code
""", [
  # Happy path with admin access
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   False, None,
   204),

  # Add user to group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   None, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   False, None,
   204),

  # Add developer user to group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   None, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   False, None,
   204),

  # At least admin access is required
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   False, None,
   403),

  # Privilege escalation not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN + 1,
   False, None,
   403),

  # Using API key is not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   False, None,
   401),

  # Non-authenticated user is blocked
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   False, None,
   401),

  # Downgrading access level of self with no other admin is not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   True, None,
   422),

  # Downgrading access level of self with other admin is allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   204),

  # Downgrading access level of self with no other non-admin user is not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   422),

  # Self-privilege escalation not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN + 1,
   True, None,
   403),
])
def test_update_access_level(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: Optional[int],
        current_access_level: Optional[int], requested_access_level: Optional[int],
        update_self: bool,
        other_user_access_level: Optional[int],
        status_code: int, user_factory, group_factory, api_client):
    client, request_body, target_user, group = common_setup(
        is_authenticated=is_authenticated,
        group_access_level=group_access_level,
        use_api_key=use_api_key,
        current_access_level=current_access_level,
        use_self=update_self,
        other_user_access_level=other_user_access_level,
        user_factory=user_factory,
        api_client=api_client)

    request_body['access_level'] = requested_access_level
    response = client.post('/api/v1/group_memberships/update_access_level/', request_body)

    assert response.status_code == status_code

    updated_access_level = UserGroupAccessLevel.access_level_for_user_in_group(
                target_user, group)

    if status_code == 204:
        assert updated_access_level == requested_access_level
    else:
        assert updated_access_level == current_access_level

@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      current_access_level, remove_self, other_user_access_level,
      status_code
""", [
  # Happy path with admin access
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False, None,
   204),

  # Remove non-member
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   None, False, None,
   204),

  # At least admin access is required
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False, None,
   403),

  # Using API key is not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False, None,
   401),

  # Non-authenticated user is blocked
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False, None,
   401),

  # Removing self with no other admin is not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True, None,
   422),

  # Removing self with other admin is allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   204),

  # Removing self with other non-admin user is not allowed
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   422),
])
def test_group_membership_removal(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: Optional[int],
        current_access_level: Optional[int], remove_self: bool,
        other_user_access_level: Optional[int],
        status_code: int, user_factory, group_factory, api_client):
    client, request_body, target_user, group = common_setup(
        is_authenticated=is_authenticated,
        group_access_level=group_access_level,
        use_api_key=use_api_key,
        current_access_level=current_access_level,
        use_self=remove_self,
        other_user_access_level=other_user_access_level,
        user_factory=user_factory,
        api_client=api_client)

    response = client.post('/api/v1/group_memberships/remove/', request_body)

    assert response.status_code == status_code

    updated_access_level = UserGroupAccessLevel.access_level_for_user_in_group(
                target_user, group)

    if status_code == 204:
        assert updated_access_level is None
    else:
        assert updated_access_level == current_access_level
