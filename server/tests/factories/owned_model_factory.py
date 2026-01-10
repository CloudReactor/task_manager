from processes.models import NamedWithUuidModel, UserGroupAccessLevel

import factory

from .uuid_model_factory import UuidModelFactory
from .group_factory import GroupFactory
from .user_factory import UserFactory


class OwnedModelFactory(UuidModelFactory):
    created_by_group = factory.SubFactory(GroupFactory)
    created_by_user = factory.SubFactory(UserFactory)

    @factory.post_generation
    def sanitize_user(model: NamedWithUuidModel, create: bool, extracted, **kwargs):
        user = model.created_by_user
        group = model.created_by_group
        if group not in user.groups.all():
            user.groups.add(group)
            user.save()

        if not UserGroupAccessLevel.objects.filter(user=user, group=group).exists():
            UserGroupAccessLevel(user=user, group=group,
                    access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER).save()
