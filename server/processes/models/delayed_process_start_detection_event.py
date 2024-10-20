from datetime import datetime

from django.db import models

from .legacy_task_execution_detection_event import LegacyTaskExecutionDetectionEvent


class DelayedProcessStartDetectionEvent(LegacyTaskExecutionDetectionEvent):
    expected_started_before = models.DateTimeField(default=datetime.now)
