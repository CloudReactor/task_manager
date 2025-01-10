import uuid

from django.db import models

from .task_execution import TaskExecution

class LegacyTaskExecutionDetectionEvent(models.Model):
    class Meta:
        abstract = True

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    task_execution = models.ForeignKey(TaskExecution,
            on_delete=models.CASCADE,
            db_column='process_execution_id')
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True)

    def __str__(self) -> str:
        return 'Task Execution ' + str(self.task_execution.uuid) + ' / ' + str(self.uuid)
