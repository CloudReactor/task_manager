from django.utils import timezone

import factory
from faker import Factory as FakerFactory

from processes.models import WorkflowTransition

from .workflow_task_instance_factory import WorkflowTaskInstanceFactory


faker = FakerFactory.create()


class WorkflowTransitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkflowTransition

    description = faker.name()
    created_at = timezone.now()
    updated_at = timezone.now()

    from_workflow_task_instance = factory.SubFactory(WorkflowTaskInstanceFactory)
    to_workflow_task_instance = factory.SubFactory(WorkflowTaskInstanceFactory)

    rule_type = WorkflowTransition.RULE_TYPE_ON_SUCCESS
    exit_codes = None
    threshold_property = ''
    threshold_comparator = ''
    custom_expression = ''
    priority = None

    ui_color = ''
    ui_line_style = ''
    ui_scale = 1.0
