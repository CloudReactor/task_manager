from datetime import datetime

from django.db import models

from .legacy_task_execution_detection_event import LegacyTaskExecutionDetectionEvent


class LegacyHeartbeatDetectionEvent(LegacyTaskExecutionDetectionEvent):
    last_heartbeat_at = models.DateTimeField(null=True)
    expected_heartbeat_at = models.DateTimeField(default=datetime.now)
    heartbeat_interval_seconds = models.IntegerField()

    class Meta:
        ordering = ['detected_at']
        db_table = 'processes_heartbeatdetectionevent'
