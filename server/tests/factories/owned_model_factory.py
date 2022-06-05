from typing import Optional

from processes.models import NamedWithUuidModel, UserGroupAccessLevel

import factory

from .group_factory import GroupFactory
from .user_factory import UserFactory


class OwnedModelFactory(factory.django.DjangoModelFactory):
    created_by_group = factory.SubFactory(GroupFactory)
    created_by_user = factory.SubFactory(UserFactory)

    @factory.post_generation
    def sanitize_user(task: NamedWithUuidModel, create: bool, extracted, **kwargs):
        user = task.created_by_user
        group = task.created_by_group
        if group not in user.groups.all():
            user.groups.add(group)

        if not UserGroupAccessLevel.objects.filter(user=user,
                group=group).exists():
            UserGroupAccessLevel(user=user, group=group,
                    access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER).save()
