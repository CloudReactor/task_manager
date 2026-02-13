from django.utils import timezone

from processes.models import MissingScheduledWorkflowExecutionEvent

import factory
from pytest_factoryboy import register

from .event_factory import EventFactory
from .workflow_factory import WorkflowFactory


@register
class MissingScheduledWorkflowExecutionEventFactory(EventFactory):
    class Meta:
        model = MissingScheduledWorkflowExecutionEvent

    workflow = factory.SubFactory(WorkflowFactory)

    expected_execution_at = factory.LazyFunction(timezone.now)
