from datetime import datetime

from django.db import models

from .task_execution_detection_event import TaskExecutionDetectionEvent


class HeartbeatDetectionEvent(TaskExecutionDetectionEvent):
    last_heartbeat_at = models.DateTimeField(null=True)
    expected_heartbeat_at = models.DateTimeField(default=datetime.now)
    heartbeat_interval_seconds = models.IntegerField()

    class Meta:
        ordering = ['detected_at']
