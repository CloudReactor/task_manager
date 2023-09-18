from typing import Optional, Type

import logging

# from django.db.models.signals import post_save
from django.dispatch import receiver

from django.contrib.auth.models import Group, User

from rest_framework.request import Request

from djoser.signals import user_activated
from djoser.views import UserViewSet as DjoserUserViewSet

from .models import SaasToken, UserGroupAccessLevel

logger = logging.getLogger(__name__)

logger.info("Loading signal handlers ...")


def add_default_group_and_saas_token(user: User) -> None:
    logger.info(f'add_default_group_and_saas_token() for {user=}')
    if user.groups.count() == 0:
        index = 0
        group: Optional[Group] = None

        while (index < 100) and (group is None):
            name = user.username

            if index > 0:
                name += f' {index}'

            index += 1

            existing_group = Group.objects.filter(name=name).first()

            if not existing_group:
                group = Group(name=name)
                group.save()
                group.user_set.add(user)
                UserGroupAccessLevel(user=user, group=group,
                        access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN).save()
                SaasToken(name=SaasToken.DEPLOYMENT_KEY_NAME,
                        description=SaasToken.DEPLOYMENT_KEY_DESCRIPTION,
                        user=user, group=group, enabled=True,
                        access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER).save()
                SaasToken(name=SaasToken.TASK_KEY_NAME,
                        description=SaasToken.TASK_KEY_DESCRIPTION,
                        user=user, group=group, enabled=True,
                        access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK).save()


# This would be nice for creating users in the Admin console, but
# djoser creates the user with is_active=True first, then sets is_active=False
# afterwards:
# https://github.com/sunscrapers/djoser/blob/786edc2bb129d7343e54d59b15b682689f534e46/djoser/serializers.py#L73
#
# So comment this out until a change is made to fix the above to never save the
# user with is_active=True in the first place.
#
# @receiver(post_save, sender=User)
# def on_user_created(sender: Type[User], instance: User, created: bool, **_kwargs) -> None:
#     if (not created) or (not instance.is_active):
#         logger.info(f'on_user_created() skipping add_default_group_and_saas_token, {created=}, {instance.is_active=}')
#         return
#
#     logger.info(f'on_user_created() calling add_default_group_and_saas_token, {created=}, {instance.is_active=}')
#     add_default_group_and_saas_token(instance)

@receiver(user_activated, sender=DjoserUserViewSet)
def on_user_activated(sender: Type[DjoserUserViewSet], user: User, request: Request, **_kwargs) -> None:
    logger.info('on_user_activated() calling add_default_group_and_saas_token')
    add_default_group_and_saas_token(user)
