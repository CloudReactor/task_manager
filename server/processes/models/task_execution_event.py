from django.db import models

from .event import Event
from .task import Task
from .task_execution import TaskExecution

class TaskExecutionEvent(Event):
    task_execution = models.ForeignKey(TaskExecution, null=True, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, null=True, on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.task_execution and not self.task:
            self.task = self.task_execution.task

        if self.task and not self.created_by_group:
            self.created_by_group = self.task.created_by_group


    def __str__(self) -> str:
        te_id = str(self.task_execution.uuid) if self.task_execution else '[REMOVED]'
        return 'Task Execution ' + te_id + ' / ' + str(self.uuid)
