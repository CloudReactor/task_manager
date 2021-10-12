from processes.models import Workflow

import factory
from faker import Factory as FakerFactory

from .group_factory import GroupFactory
from .user_factory import UserFactory
from .run_environment_factory import RunEnvironmentFactory

faker = FakerFactory.create()


class WorkflowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workflow

    name = factory.Sequence(lambda n: f'workflow_{n}')

    created_by_group = factory.SubFactory(GroupFactory)
    created_by_user = factory.SubFactory(UserFactory)

    run_environment = factory.SubFactory(RunEnvironmentFactory)

    max_age_seconds = 3600
    default_max_retries = 0
    latest_workflow_execution = None
    aws_scheduled_execution_rule_name = ''
    aws_scheduled_event_rule_arn = ''
    aws_event_target_rule_name = ''
    aws_event_target_id = ''