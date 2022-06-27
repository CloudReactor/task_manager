from datetime import datetime

from django.db import models

from .task_execution_detection_event import TaskExecutionDetectionEvent


class DelayedProcessStartDetectionEvent(TaskExecutionDetectionEvent):
    expected_started_before = models.DateTimeField(default=datetime.now)
