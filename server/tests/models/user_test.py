import pytest

from django.contrib.auth.models import Group, User


from djoser.signals import user_activated
from djoser.views import UserViewSet as DjoserUserViewSet

from processes.models import (
    SaasToken, UserGroupAccessLevel
)
from processes.common.request_helpers import request_for_context

def ensure_user_has_default_group_and_saas_token(user):
    assert user.groups.count() == 1
    group = user.groups.first()
    assert group.name == 'foo'
    ugal_list = list(user.group_access_levels.all())
    assert len(ugal_list) == 1
    ugal = ugal_list[0]
    assert ugal.user == user
    assert ugal.group == group
    assert ugal.access_level == UserGroupAccessLevel.ACCESS_LEVEL_ADMIN
    tokens = list(SaasToken.objects.filter(user=user).order_by('access_level'))
    assert len(tokens) == 2

    assert tokens[0].name == SaasToken.TASK_KEY_NAME
    assert tokens[0].description == SaasToken.TASK_KEY_DESCRIPTION
    assert tokens[0].group == group
    assert tokens[0].access_level == UserGroupAccessLevel.ACCESS_LEVEL_TASK

    assert tokens[1].name == SaasToken.DEPLOYMENT_KEY_NAME
    assert tokens[1].description == SaasToken.DEPLOYMENT_KEY_DESCRIPTION
    assert tokens[1].group == group
    assert tokens[1].access_level == UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER

# See signal_handlers.py for why this is commented out.
# @pytest.mark.django_db
# def test_group_and_saas_token_creation():
#     user = User(username='foo', is_active=True)
#     user.save()
#     ensure_user_has_default_group_and_saas_token(user)

@pytest.mark.django_db
def test_inactive_user_save_then_activate():
    user = User(username='foo', is_active=False)
    user.save()
    assert user.groups.count() == 0
    ugal_list = list(user.group_access_levels.all())
    assert len(ugal_list) == 0
    tokens = list(SaasToken.objects.filter(user=user))
    assert len(tokens) == 0

    user_activated.send(sender=DjoserUserViewSet, user=user,
            request=request_for_context())
    ensure_user_has_default_group_and_saas_token(user)

@pytest.mark.django_db
def test_conflicting_group_creation():
    existing_group = Group(name='conflict')
    existing_group.save()
    user = User(username='conflict', is_active=False)
    user.save()
    user_activated.send(sender=DjoserUserViewSet, user=user,
            request=request_for_context())
    assert user.groups.count() == 1
    group = user.groups.first()
    assert group.name == 'conflict 1'
