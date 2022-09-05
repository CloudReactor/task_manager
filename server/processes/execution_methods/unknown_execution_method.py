from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..models import (
      Task
    )

from .execution_method import ExecutionMethod

class UnknownExecutionMethod(ExecutionMethod):
    NAME = 'Unknown'

    def __init__(self, task: 'Task', task_execution: Optional['TaskExecution']):
        super().__init__(self.NAME, task=task, task_execution=task_execution)
