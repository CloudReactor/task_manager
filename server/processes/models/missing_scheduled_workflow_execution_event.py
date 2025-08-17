from typing import Optional

from .workflow import Workflow
from .workflow_execution import WorkflowExecution
from .workflow_execution_event import WorkflowExecutionEvent
from .missing_scheduled_execution_event import MissingScheduledExecutionEvent


class MissingScheduledWorkflowExecutionEvent(WorkflowExecutionEvent, MissingScheduledExecutionEvent):
    @property
    def schedulable_instance(self) -> Workflow:
        return self.workflow

    @property
    def resolving_execution(self) -> Optional[WorkflowExecution]:
        return self.workflow_execution
