import logging

from typing import Optional

from .execution import Execution
from .schedulable import Schedulable
from .execution_status_change_event import ExecutionStatusChangeEvent
from .workflow_execution import WorkflowExecution
from .workflow_execution_event import WorkflowExecutionEvent


logger = logging.getLogger(__name__)


class WorkflowExecutionStatusChangeEvent(ExecutionStatusChangeEvent, WorkflowExecutionEvent):
    ERROR_SUMMARY_TEMPLATE = \
        """Workflow '{{workflow.name}}' finished with status {{workflow_execution.status}}"""

    ERROR_MESSAGE_TEMPLATE = \
        """Workflow '{{workflow.name}}' finished with status {{workflow_execution.status}}"""

    def __init__(self, *args, **kwargs):
        from ..services.notification_generator import NotificationGenerator

        super().__init__(*args, **kwargs)

        self.successful_status = WorkflowExecution.Status.SUCCEEDED
        self.failed_status = WorkflowExecution.Status.FAILED
        self.terminated_status = WorkflowExecution.Status.TERMINATED_AFTER_TIME_OUT

        # Only generate error_summary if workflow_execution is set
        if self.workflow_execution:
            notification_generator = NotificationGenerator()

            template_params = notification_generator.make_template_params(
                    workflow_execution=self.workflow_execution,
                    severity=self.severity_label)

            self.error_summary = notification_generator.generate_text(
                    template_params=template_params,
                    template=self.ERROR_SUMMARY_TEMPLATE,
                    workflow_execution=self.workflow_execution)


    def get_schedulable(self) -> Optional[Schedulable]:
        if self.workflow:
            return self.workflow

        if self.workflow_execution:
            return self.workflow_execution.workflow

        return None

    def get_execution(self) -> Optional[Execution]:
        return self.workflow_execution
