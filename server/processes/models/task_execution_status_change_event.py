import logging

from typing import Optional, override

from .task import Task
from .task_execution import TaskExecution
from .execution_status_change_event import ExecutionStatusChangeEvent
from .task_execution_event import TaskExecutionEvent


logger = logging.getLogger(__name__)


class TaskExecutionStatusChangeEvent(ExecutionStatusChangeEvent, TaskExecutionEvent):
    ERROR_SUMMARY_TEMPLATE = \
        """Execution {{task_execution.uuid}} of Task '{{task.name}}' finished with status {{task_execution.status}}"""

    ERROR_MESSAGE_TEMPLATE = \
        """Execution {{task_execution.uuid}} of Task '{{task.name}}' finished with status {{task_execution.status}}"""

    def __init__(self, *args, **kwargs):
        from ..services.notification_generator import NotificationGenerator

        super().__init__(*args, **kwargs)

        self.successful_status = TaskExecution.Status.SUCCEEDED
        self.failed_status = TaskExecution.Status.FAILED
        self.terminated_status = TaskExecution.Status.TERMINATED_AFTER_TIME_OUT

        # Only generate error_summary if task_execution is set
        if self.task_execution:
            notification_generator = NotificationGenerator()

            template_params = notification_generator.make_template_params(
                    task_execution=self.task_execution,
                    severity=self.severity_label)

            self.error_summary = notification_generator.generate_text(
                    template_params=template_params,
                    template=self.ERROR_SUMMARY_TEMPLATE,
                    task_execution=self.task_execution)


    @override
    def get_schedulable(self) -> Optional['Task']:
        if self.task:
            return self.task

        if self.task_execution:
            return self.task_execution.task

        return None

    @override
    def get_execution(self) -> Optional['TaskExecution']:
        return self.task_execution
