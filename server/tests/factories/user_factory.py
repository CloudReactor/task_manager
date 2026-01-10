from typing import List

import factory

from faker import Factory as FakerFactory

from django.contrib.auth.models import User, Group

from pytest_factoryboy import register

from processes.models import UserGroupAccessLevel


faker = FakerFactory.create()


@register
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    password = 'foobar!1234'

    @factory.post_generation
    def populate_groups(user: User, create: bool, extracted: List[Group], **_kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                user.groups.add(group)
        else:
          default_group, did_create_group = Group.objects.get_or_create(
                  name=user.username
          )
          user.groups.add(default_group)

          if did_create_group:
              UserGroupAccessLevel.objects.get_or_create(user=user,
                      group=default_group,
                      access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
              
        user.save()
