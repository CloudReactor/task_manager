from django.db import models

from .event import Event
from .task import Task
from .task_execution import TaskExecution

class TaskExecutionEvent(Event):
    task_execution = models.ForeignKey(TaskExecution, null=True, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, null=True, on_delete=models.CASCADE)

    def __str__(self):
        te_id = str(self.task_execution.uuid) if self.task_execution else '[REMOVED]'
        return 'Task Execution ' + te_id + ' / ' + str(self.uuid)
