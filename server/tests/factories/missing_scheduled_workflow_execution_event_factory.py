from django.utils import timezone

from processes.models import MissingScheduledWorkflowExecutionEvent

import factory
from pytest_factoryboy import register

from .group_factory import GroupFactory
from .workflow_factory import WorkflowFactory


@register
class MissingScheduledWorkflowExecutionEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MissingScheduledWorkflowExecutionEvent

    created_by_group = factory.SubFactory(GroupFactory)
    workflow = factory.SubFactory(WorkflowFactory)

    severity = MissingScheduledWorkflowExecutionEvent.Severity.ERROR
    expected_execution_at = factory.LazyFunction(timezone.now)
