from __future__ import annotations

from typing import TYPE_CHECKING, override

from ..common.utils import strip_prefix_before_last_dot

from .task_event import TaskEvent
from .task_execution_event import TaskExecutionEvent
from .missing_scheduled_execution_event import MissingScheduledExecutionEvent

if TYPE_CHECKING:
    from .task_execution import TaskExecution

class MissingScheduledTaskExecutionEvent(TaskExecutionEvent, MissingScheduledExecutionEvent):
    @property
    @override
    def resolving_execution(self) -> TaskExecution | None:
        return self.task_execution

    @override
    def __str__(self) -> str:
        # Because TaskExecutionEvent uses the possibly missing Task Execution
        return TaskEvent.__str__(self)
