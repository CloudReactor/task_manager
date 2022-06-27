from processes.models import Workflow

import factory
from faker import Factory as FakerFactory

from .owned_model_factory import OwnedModelFactory
from .run_environment_factory import RunEnvironmentFactory

faker = FakerFactory.create()


class WorkflowFactory(OwnedModelFactory):
    class Meta:
        model = Workflow

    name = factory.Sequence(lambda n: f'workflow_{n}')

    run_environment = factory.SubFactory(RunEnvironmentFactory,
        created_by_user=factory.SelfAttribute("..created_by_user"),
        created_by_group=factory.SelfAttribute("..created_by_group"))

    max_age_seconds = 3600
    default_max_retries = 0
    latest_workflow_execution = None
    aws_scheduled_execution_rule_name = ''
    aws_scheduled_event_rule_arn = ''
    aws_event_target_rule_name = ''
    aws_event_target_id = ''