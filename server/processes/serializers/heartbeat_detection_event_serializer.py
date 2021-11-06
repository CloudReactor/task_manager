import logging

from rest_framework import serializers

from processes.models import HeartbeatDetectionEvent
from .task_execution_serializer import TaskExecutionSerializer

logger = logging.getLogger(__name__)


class HeartbeatDetectionEventSerializer(serializers.ModelSerializer):
    """
    Represents an event that is created when a missing heartbeat from a
    Task Execution is detected.
    """

    class Meta:
        model = HeartbeatDetectionEvent
        fields = ('uuid', 'task_execution', 'detected_at',
                  'resolved_at', 'last_heartbeat_at', 'expected_heartbeat_at',
                  'heartbeat_interval_seconds',)

    task_execution = TaskExecutionSerializer()
