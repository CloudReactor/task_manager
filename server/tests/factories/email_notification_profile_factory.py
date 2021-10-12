from typing import List

from processes.models import EmailNotificationProfile

import factory
from faker import Factory as FakerFactory

from .group_factory import GroupFactory
from .user_factory import UserFactory

faker = FakerFactory.create()


class EmailNotificationProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailNotificationProfile

    name = factory.Sequence(lambda n: f'pdp_{n}')

    created_by_group = factory.SubFactory(GroupFactory)
    created_by_user = factory.SubFactory(UserFactory)

    subject_template = factory.Faker('random_letters')
    body_template = factory.Faker('random_letters')
    to_addresses = [factory.Faker('ascii_company_email')]
    cc_addresses: List[str] = []
    bcc_addresses: List[str] = []
