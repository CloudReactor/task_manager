from __future__ import annotations

import logging

from typing import TYPE_CHECKING, override

from .execution_status_change_event import ExecutionStatusChangeEvent
from .task_execution_event import TaskExecutionEvent


if TYPE_CHECKING:
    from .task_execution import TaskExecution
    from .task import Task


logger = logging.getLogger(__name__)


class TaskExecutionStatusChangeEvent(ExecutionStatusChangeEvent, TaskExecutionEvent):
    ERROR_SUMMARY_TEMPLATE = \
        """Execution {{task_execution.uuid}} of Task '{{task.name}}' finished with status {{task_execution.status}}"""

    ERROR_MESSAGE_TEMPLATE = \
        """Execution {{task_execution.uuid}} of Task '{{task.name}}' finished with status {{task_execution.status}}"""

    def __init__(self, *args, **kwargs):        
        from ..services.notification_generator import NotificationGenerator

        super().__init__(*args, **kwargs)

        # Only generate error_summary if task_execution is set
        if self.task_execution:
            notification_generator = NotificationGenerator()

            template_params = notification_generator.make_template_params(
                    task_execution=self.task_execution,
                    severity=self.severity_label)

            self.error_summary = notification_generator.generate_text(
                    template_params=template_params,
                    template=__class__.ERROR_SUMMARY_TEMPLATE,
                    task_execution=self.task_execution)


    @override
    def get_schedulable(self) -> Task | None:
        if self.task:
            return self.task

        if self.task_execution:
            return self.task_execution.task

        return None

    @override
    def get_execution(self) -> TaskExecution | None:
        return self.task_execution
