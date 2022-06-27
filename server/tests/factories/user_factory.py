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

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    password = 'foobar!1234'

    # Copied straight from https://factoryboy.readthedocs.io/en/latest/recipes.html
    @factory.post_generation
    def groups(self: User, create: bool, extracted: List[Group], **_kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                self.groups.add(group)
        else:
          default_group, did_create_group = Group.objects.get_or_create(
                  name=self.username
          )
          self.groups.add(default_group)

          if did_create_group:
              UserGroupAccessLevel.objects.get_or_create(user=self,
                      group=default_group,
                      access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)
