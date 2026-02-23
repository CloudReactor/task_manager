from __future__ import annotations

from typing import TYPE_CHECKING, override

from .task_event import TaskEvent
from .task_execution_event import TaskExecutionEvent
from .missing_scheduled_execution_event import MissingScheduledExecutionEvent

if TYPE_CHECKING:
    from .task_execution import TaskExecution

class MissingScheduledTaskExecutionEvent(TaskExecutionEvent, MissingScheduledExecutionEvent):
    def __init__(self, *args, **kwargs):
        # Call TaskExecutionEvent's __init__ which will call the parent chain
        TaskExecutionEvent.__init__(self, *args, **kwargs)
        # Explicitly call MissingScheduledExecutionEvent's __init__ to set grouping_key and other fields
        MissingScheduledExecutionEvent.__init__(self, *args, **kwargs)

    @property
    @override
    def resolving_execution(self) -> TaskExecution | None:
        return self.task_execution

    @override
    def __str__(self) -> str:
        # Because TaskExecutionEvent uses the possibly missing Task Execution
        return TaskEvent.__str__(self)
