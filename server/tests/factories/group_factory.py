import factory
from faker import Factory as FakerFactory

from django.contrib.auth.models import Group

from pytest_factoryboy import register


@register
class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = factory.Sequence(lambda n: f'group_{n}')
