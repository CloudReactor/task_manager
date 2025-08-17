from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .task_execution_event import TaskExecutionEvent
from .missing_scheduled_execution_event import MissingScheduledExecutionEvent

if TYPE_CHECKING:
    from .task_execution import TaskExecution

class MissingScheduledTaskExecutionEvent(TaskExecutionEvent, MissingScheduledExecutionEvent):
    @property
    def resolving_execution(self) -> Optional[TaskExecution]:
        return self.task_execution
