from processes.models import Execution, WorkflowExecutionStatusChangeEvent

import factory
from pytest_factoryboy import register

from .event_factory import EventFactory
from .workflow_factory import WorkflowFactory
from .workflow_execution_factory import WorkflowExecutionFactory


@register
class WorkflowExecutionStatusChangeEventFactory(EventFactory):
    class Meta:
        model = WorkflowExecutionStatusChangeEvent

    workflow = factory.SubFactory(WorkflowFactory)
    workflow_execution = factory.SubFactory(WorkflowExecutionFactory)

    status = Execution.Status.FAILED
