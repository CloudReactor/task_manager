from typing import cast, Optional

from django.conf import settings
from django.db import models

from django.contrib.auth.models import Group, AbstractUser, User
from django.utils.translation import gettext_lazy as _


class UserGroupAccessLevel(models.Model):
    ACCESS_LEVEL_OBSERVER = 1
    ACCESS_LEVEL_TASK = 50
    ACCESS_LEVEL_SUPPORT = 100
    ACCESS_LEVEL_DEVELOPER = 500
    ACCESS_LEVEL_ADMIN = 1000

    class Meta:
        unique_together = (('user', 'group',),)

    user = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            related_name='group_access_levels',
            on_delete=models.CASCADE,
            verbose_name=_("User"))

    access_level = models.IntegerField()

    group = models.ForeignKey(Group,
            related_name='user_access_levels',
            on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'UGA: user={self.user.username}, group={self.group.name}, access_level={self.access_level}'

    @staticmethod
    def access_level_for_user_in_group(user: AbstractUser, group: Group) -> Optional[int]:
        if not user.is_authenticated:
            return None

        authenticated_user = cast(User, user)
        access_level = authenticated_user.group_access_levels.filter(group=group) \
              .values_list('access_level', flat=True).first()

        if access_level:
            return access_level

        if user.groups.filter(pk=group.pk).exists():
            return UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER

        return None

    @staticmethod
    def admin_count(group: Group) -> int:
        return UserGroupAccessLevel.objects.filter(group=group,
                access_level__gte=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN).count()
