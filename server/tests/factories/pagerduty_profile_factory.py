
from processes.models import PagerDutyProfile

import factory
from faker import Factory as FakerFactory

from .group_factory import GroupFactory
from .user_factory import UserFactory

faker = FakerFactory.create()


class PagerDutyProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PagerDutyProfile

    name = factory.Sequence(lambda n: f'pdp_{n}')

    created_by_group = factory.SubFactory(GroupFactory)
    created_by_user = factory.SubFactory(UserFactory)

    integration_key = factory.Faker('random_letters')
    default_event_severity = 'error'
