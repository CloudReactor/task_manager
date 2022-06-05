
from processes.models import RunEnvironment, UserGroupAccessLevel

import factory
from faker import Factory as FakerFactory

from .group_factory import GroupFactory
from .user_factory import UserFactory
from .owned_model_factory import OwnedModelFactory

faker = FakerFactory.create()


class RunEnvironmentFactory(OwnedModelFactory):
    class Meta:
        model = RunEnvironment

    name = factory.Sequence(lambda n: f'run_environment_{n}')

    aws_account_id = '123456789012'
    aws_default_region = 'us-west-1'
    aws_events_role_arn = 'arn:aws:iam::123456789012:role/cloudreactor_assumable'
