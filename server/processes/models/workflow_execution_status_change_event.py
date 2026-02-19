from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from .execution_status_change_event import ExecutionStatusChangeEvent
from .workflow_execution_event import WorkflowExecutionEvent

if TYPE_CHECKING:
    from .workflow import Workflow
    from .workflow_execution import WorkflowExecution



logger = logging.getLogger(__name__)


class WorkflowExecutionStatusChangeEvent(ExecutionStatusChangeEvent, WorkflowExecutionEvent):
    ERROR_SUMMARY_TEMPLATE = \
        """Workflow '{{workflow.name}}' finished with status {{workflow_execution.status}}"""

    ERROR_MESSAGE_TEMPLATE = \
        """Workflow '{{workflow.name}}' finished with status {{workflow_execution.status}}"""

    def __init__(self, *args, **kwargs):
        from ..services.notification_generator import NotificationGenerator

        super().__init__(*args, **kwargs)

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


    def get_schedulable(self) -> Workflow | None:
        if self.workflow:
            return self.workflow

        if self.workflow_execution:
            return self.workflow_execution.workflow

        return None

    def get_execution(self) -> WorkflowExecution | None:
        return self.workflow_execution
