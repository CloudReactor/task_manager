from typing import Any, Optional, Tuple

import uuid
from uuid import UUID
from urllib.parse import quote

from django.utils.html import escape

from django.contrib.auth.models import Group, User

from processes.common.request_helpers import context_with_request
from processes.models import (
    Invitation,
    UserGroupAccessLevel
)
from processes.serializers.invitation_serializer import InvitationSerializer

import pytest

from conftest import *


@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      is_user_existing, is_existing_user_active, existing_user_access_level,
      invitation_access_level, status_code
   """, [
       (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
        False, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, 401),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
        False, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, 201),
       # API Key not allowed
       (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
        False, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, 401),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
        False, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, 201),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
        False, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, 201),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
        False, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_TASK, 403),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, False,
        False, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_TASK, 403),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, False,
        False, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, 403),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
        True, True, None,
        UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, 200),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
        True, True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, 200),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
        True, True, None,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, 200),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
        True, True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, 200),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
        True, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT, 201),
       (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
        True, True, None,
        UserGroupAccessLevel.ACCESS_LEVEL_TASK, 403),
       (True, None, False,
        False, False, None,
        UserGroupAccessLevel.ACCESS_LEVEL_TASK, 403),
   ]
)
def test_invitation_creation(is_authenticated: bool,
        group_access_level: Optional[int], use_api_key: bool,
        invitation_access_level: Optional[int], is_user_existing: bool,
        is_existing_user_active: bool,
        existing_user_access_level: Optional[int],
        status_code: int, user_factory, api_client, mailoutbox):
    user = user_factory()

    if group_access_level is None:
      group = Group(name='Another Group')
      group.save()
    else:
      group = user.groups.first()
      ugal = UserGroupAccessLevel.objects.get(user=user, group=group)
      ugal.access_level = group_access_level
      ugal.save()

    to_email = 'foo@bar.com'

    existing_user = None
    if is_user_existing:
        existing_user = User(username=to_email, email=to_email,
                is_active=is_existing_user_active)
        existing_user.save()
        if existing_user_access_level is not None:
            existing_user.groups.add(group)
            if existing_user_access_level > UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER:
                UserGroupAccessLevel(user=existing_user, group=group,
                        access_level=existing_user_access_level).save()

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level)

    request_body: dict[str, Any] = {
      'to_email': to_email,
      'group': {
        'id': group.pk
      }
    }

    if invitation_access_level != UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER:
        request_body['group_access_level'] = invitation_access_level

    response = client.post('/api/v1/invitations/', request_body)

    assert response.status_code == status_code

    if status_code == 201:
        invitation = Invitation.objects.get(group=group, to_email=to_email)
        if invitation_access_level is None:
            assert invitation.group_access_level == UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER
        else:
            assert invitation.group_access_level == invitation_access_level
        assert invitation.invited_user.username == to_email
        assert invitation.invited_user.email == to_email
        assert not invitation.invited_user.is_active

        assert len(mailoutbox) == 1
        m = mailoutbox[0]
        assert m.from_email == 'webmaster@cloudreactor.io'
        assert list(m.to) == [to_email]
        assert group.name in m.subject
        assert escape(group.name) in m.body
        assert invitation.acceptance_link in m.body
    else:
        assert len(mailoutbox) == 0

    if status_code == 200:
        assert not Invitation.objects.filter(group=group, to_email=to_email).exists()
        assert existing_user is not None
        assert existing_user.is_active
        assert UserGroupAccessLevel.access_level_for_user_in_group(
                user=existing_user, group=group) == max(
                invitation_access_level or UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
                existing_user_access_level or UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER)

    if existing_user and (status_code >= 300):
        assert UserGroupAccessLevel.access_level_for_user_in_group(
                user=existing_user, group=group) == existing_user_access_level



def make_invitation(user_factory, group_access_level: Optional[int] = None,
      group: Optional[Group] = None) -> Invitation:
    if group_access_level is None:
        group_access_level = UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    invited_by_user = user_factory()
    group = group or invited_by_user.groups.first()

    invited_user = User(username='foo@bar.com', email='foo@bar.com', is_active=False)
    invited_user.save()

    invitation = Invitation(to_email='foo@bar.com', invited_by_user=invited_by_user,
            invited_user=invited_user,
            group=group, group_access_level=group_access_level,
            confirmation_code='ABC')
    invitation.save()

    return invitation


@pytest.mark.django_db
@pytest.mark.parametrize("""
      send_invitation_code_type, status_code
    """, [
      (SEND_ID_CORRECT, 200),
      (SEND_ID_NOT_FOUND, 200),
      (SEND_ID_NONE, 400),
    ]
)
def test_invitation_list(send_invitation_code_type: str, status_code: int,
      user_factory, api_client):
    invitation = make_invitation(user_factory)

    invitation_code: Optional[str] = 'ABC'
    if send_invitation_code_type == SEND_ID_NOT_FOUND:
        invitation_code = 'NOTREAL'
    elif send_invitation_code_type == SEND_ID_NONE:
        invitation_code = None

    params = {}
    if send_invitation_code_type != SEND_ID_NONE:
        params = {
          'confirmation_code': invitation_code
        }

    response = api_client.get('/api/v1/invitations/', params)

    assert response.status_code == status_code

    if status_code == 200:
        page = response.data
        if send_invitation_code_type == SEND_ID_CORRECT:
            assert page['count'] == 1
            result = page['results'][0]
            context = context_with_request()
            assert result == InvitationSerializer(invitation, context=context).data
        else:
            assert page['count'] == 0
            assert len(page['results']) == 0

def common_setup(is_authenticated: bool, group_access_level: Optional[int],
        use_api_key: bool, send_uuid_type: str, request_by_inviter: bool,
        user_factory, api_client: APIClient) -> Tuple[Invitation, UUID, APIClient]:
    invitation = make_invitation(user_factory)

    invitation_uuid = invitation.uuid
    if send_uuid_type == SEND_ID_NOT_FOUND:
        invitation_uuid = uuid.uuid4()

    request_user = invitation.invited_by_user
    if send_uuid_type == SEND_ID_IN_WRONG_GROUP:
        request_user = user_factory()
    else:
        if not request_by_inviter:
            request_user = user_factory()

        set_group_access_level(user=request_user, group=invitation.group,
                access_level=group_access_level)

    api_key_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN if use_api_key else None
    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=request_user,
            group=invitation.group,
            api_key_access_level=api_key_access_level)

    return invitation, invitation_uuid, client


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level, use_api_key,
  send_uuid_type, request_by_inviter, status_code
""", [
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, True, 200),

  # Another admin of the group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, False, 200),

  # Admin access is required
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
   SEND_ID_CORRECT, True, 403),

  # Not found invitation
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_NOT_FOUND, True, 404),

  # Invitation not in user's group
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_IN_WRONG_GROUP, True, 404),

  # User with no access to the group gets a 404
  (True, None, False,
   SEND_ID_CORRECT, True, 404),

  # Anonymous user gets 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
   SEND_ID_CORRECT, True, 401),

  # Authentication via API key gets 401
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, True,
   SEND_ID_CORRECT, True, 401),
])
def test_invitation_fetch(
        is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
        send_uuid_type: str, request_by_inviter: bool, status_code: int,
        user_factory, api_client):
    invitation, invitation_uuid, client = common_setup(
        is_authenticated=is_authenticated,
        group_access_level=group_access_level, use_api_key=use_api_key,
        send_uuid_type=send_uuid_type, request_by_inviter=request_by_inviter,
        user_factory=user_factory, api_client=api_client)

    response = client.get(f'/api/v1/invitations/{quote(str(invitation_uuid))}/')

    assert response.status_code == status_code

    if status_code == 200:
        assert response.data == InvitationSerializer(invitation,
                context=context_with_request()).data

@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      send_uuid_type, request_by_inviter, status_code
    """, [
      (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
       SEND_ID_CORRECT, True, 405),

      (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
       SEND_ID_NOT_FOUND, True, 405),

      (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
       SEND_ID_IN_WRONG_GROUP, True, 405),

      # At least Admin access is required
      (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
       SEND_ID_CORRECT, True, 405),

      # User with no access to the group should be denied
      (True, None, False,
       SEND_ID_CORRECT, True, 405),

      # Anonymous user is not allowed
      (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
       SEND_ID_CORRECT, True, 405),

      # API key not allowed to be used to authenticate
      (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
       SEND_ID_CORRECT, True, 405),
    ]
)
def test_invitation_update_access_control(
      is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
      send_uuid_type: str, request_by_inviter: bool,
      status_code: int,
      user_factory, group_factory, api_client):
    invitation, invitation_uuid, client = common_setup(
        is_authenticated=is_authenticated,
        group_access_level=group_access_level, use_api_key=use_api_key,
        send_uuid_type=send_uuid_type, request_by_inviter=request_by_inviter,
        user_factory=user_factory, api_client=api_client)

    response = client.patch(
            f'/api/v1/invitations/{quote(str(invitation_uuid))}/', {})

    assert response.status_code == status_code


@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_authenticated, group_access_level, use_api_key,
      send_uuid_type, request_by_inviter, status_code
    """, [
      (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
       SEND_ID_CORRECT, True, 204),

      (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
       SEND_ID_NOT_FOUND, True, 404),

      (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
       SEND_ID_IN_WRONG_GROUP, True, 404),

      # At least Admin access is required
      (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER, False,
       SEND_ID_CORRECT, True, 403),

      # User with no access to the group should be denied
      (True, None, False,
       SEND_ID_CORRECT, True, 404),

      # Anonymous user is not allowed
      (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, False,
       SEND_ID_CORRECT, True, 401),

      # API key not allowed to be used to authenticate
      (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, True,
       SEND_ID_CORRECT, True, 401),
    ]
)
def test_invitation_removal(
      is_authenticated: bool, group_access_level: Optional[int], use_api_key: bool,
      send_uuid_type: str, request_by_inviter: bool,
      status_code: int,
      user_factory, group_factory, api_client):
    invitation, invitation_uuid, client = common_setup(
        is_authenticated=is_authenticated,
        group_access_level=group_access_level, use_api_key=use_api_key,
        send_uuid_type=send_uuid_type, request_by_inviter=request_by_inviter,
        user_factory=user_factory, api_client=api_client)

    response = client.delete(f'/api/v1/invitations/{quote(str(invitation_uuid))}/')

    assert response.status_code == status_code

    exists = Invitation.objects.filter(uuid=invitation.uuid).exists()

    if status_code == 204:
        assert not exists
    else:
        assert exists

@pytest.mark.django_db
@pytest.mark.parametrize("""
      is_invitation_code_valid, status_code
    """, [
      (True, 204),
      (False, 404),
    ]
)
def test_invitation_acceptance(is_invitation_code_valid: bool, status_code: int,
      user_factory, api_client):
  invitation = make_invitation(user_factory)

  invitation_code = 'ABC'
  if not is_invitation_code_valid:
      invitation_code = 'WRONG'

  response = api_client.post('/api/v1/invitations/accept/', {
      'confirmation_code': invitation_code,
      'username': 'foo@bar.com',
      'password': '10295TS@1385'
  })

  assert response.status_code == status_code

  invitation.refresh_from_db()

  if is_invitation_code_valid:
      assert invitation.accepted_at is not None
      assert invitation.invited_user.is_active
      assert UserGroupAccessLevel.access_level_for_user_in_group(
              invitation.invited_user, invitation.group) == UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
  else:
      assert invitation.accepted_at is None
      assert not invitation.invited_user.is_active
      assert UserGroupAccessLevel.access_level_for_user_in_group(
              invitation.invited_user, invitation.group) is None
