
from processes.models import RunEnvironment

import factory
from faker import Factory as FakerFactory

from .group_factory import GroupFactory
from .user_factory import UserFactory

faker = FakerFactory.create()


class RunEnvironmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RunEnvironment

    name = factory.Sequence(lambda n: f'run_environment_{n}')

    created_by_group = factory.SubFactory(GroupFactory)
    created_by_user = factory.SubFactory(UserFactory)

    aws_account_id = '123456789012'
    aws_default_region = 'us-west-1'
    aws_events_role_arn = 'arn:aws:iam::123456789012:role/cloudreactor_assumable'
