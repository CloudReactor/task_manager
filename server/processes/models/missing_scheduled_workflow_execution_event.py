from typing import override

from .workflow import Workflow
from .workflow_execution import WorkflowExecution
from .workflow_event import WorkflowEvent
from .workflow_execution_event import WorkflowExecutionEvent
from .missing_scheduled_execution_event import MissingScheduledExecutionEvent


class MissingScheduledWorkflowExecutionEvent(WorkflowExecutionEvent, MissingScheduledExecutionEvent):
    @property
    @override
    def schedulable_instance(self) -> Workflow:
        return self.workflow

    @property
    @override
    def resolving_execution(self) -> WorkflowExecution | None:
        return self.workflow_execution

    @override
    def __str__(self) -> str:
        # Because WorkflowExecutionEvent uses the possibly missing Workflow Execution
        return WorkflowEvent.__str__(self)
