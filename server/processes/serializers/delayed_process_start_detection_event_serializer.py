import logging

from rest_framework import serializers

from processes.models import DelayedProcessStartDetectionEvent
from .task_execution_serializer import TaskExecutionSerializer

logger = logging.getLogger(__name__)


class DelayedProcessStartDetectionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DelayedProcessStartDetectionEvent
        fields = ('uuid', 'task_execution', 'detected_at',
                  'expected_started_before', 'resolved_at',)

    task_execution = TaskExecutionSerializer()
