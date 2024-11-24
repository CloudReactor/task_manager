from datetime import datetime

from django.db import models

from .legacy_task_execution_detection_event import LegacyTaskExecutionDetectionEvent

# FUTURE: convert to new event model
class DelayedProcessStartDetectionEvent(LegacyTaskExecutionDetectionEvent):
    expected_started_before = models.DateTimeField(default=datetime.now)
