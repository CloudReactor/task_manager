from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import (
      Task, TaskExecution
    )

from .execution_method import ExecutionMethod

class UnknownExecutionMethod(ExecutionMethod):
    NAME = 'Unknown'

    def __init__(self, task: Task | None,
            task_execution: TaskExecution | None):
        super().__init__(self.NAME, task=task, task_execution=task_execution)
