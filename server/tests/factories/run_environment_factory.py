
from processes.models import RunEnvironment, UserGroupAccessLevel

import factory
from faker import Factory as FakerFactory

from .owned_model_factory import OwnedModelFactory

faker = FakerFactory.create()


class RunEnvironmentFactory(OwnedModelFactory):
    class Meta:
        model = RunEnvironment

    name = factory.Sequence(lambda n: f'run_environment_{n}')

    aws_account_id = '123456789012'
    aws_default_region = 'us-west-1'
    aws_events_role_arn = 'arn:aws:iam::123456789012:role/cloudreactor_assumable'
    aws_assumed_role_external_id = 'DEADBEEF'
    aws_ecs_default_execution_role = 'arn:aws:iam::123456789012:role/execution'
    aws_ecs_default_cluster_arn = 'arn:aws:ecs:us-east-2:123456789012:cluster/MyECSCluster'
    aws_default_subnets = ['subnet-123456']
    aws_ecs_default_security_groups = ['sg-123456']
