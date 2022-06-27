import logging

from rest_framework import serializers

from processes.models import DelayedProcessStartDetectionEvent
from .task_execution_serializer import TaskExecutionSerializer

logger = logging.getLogger(__name__)


class DelayedTaskStartDetectionEventSerializer(serializers.ModelSerializer):
    """
    Represents an event that is created when a delay in a Task starting is
    detected.
    """

    class Meta:
        model = DelayedProcessStartDetectionEvent
        fields = ('uuid', 'task_execution', 'detected_at',
                  'expected_started_before', 'resolved_at',)

    task_execution = TaskExecutionSerializer()
