from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import (
      Task
    )

from .execution_method import ExecutionMethod

class UnknownExecutionMethod(ExecutionMethod):
    NAME = 'Unknown'

    def __init__(self, task: 'Task'):
        super().__init__(self.NAME, task)
