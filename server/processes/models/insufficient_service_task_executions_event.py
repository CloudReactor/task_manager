from django.db import models

from .task_event import TaskEvent

class InsufficientServiceTaskExecutionsEvent(TaskEvent):
    interval_start_at = models.DateTimeField(null=True)
    interval_end_at = models.DateTimeField(null=True)
    detected_concurrency = models.IntegerField(null=True)
    required_concurrency = models.IntegerField(null=True)
