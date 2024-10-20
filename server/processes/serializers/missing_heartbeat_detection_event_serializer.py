from rest_framework import serializers

from ..models import MissingHeartbeatDetectionEvent

from .task_execution_serializer import TaskExecutionSerializer

# TODO: do we need this class?

class MissingHeartbeatDetectionEventSerializer(serializers.ModelSerializer):
    """
    Serializes a missing heartbeat detection event.
    """

    class Meta:
        model = MissingHeartbeatDetectionEvent
        fields = ('uuid', 'event_at', 'detected_at', 'severity',
                  'error_summary',
                  'error_details_message',
                  'grouping_key', 'resolved_at', 'resolved_event',
                  'task_execution',
                  'last_heartbeat_at', 'expected_heartbeat_at',
                  'heartbeat_interval_seconds',)

    task_execution = TaskExecutionSerializer()
    resolved_event = serializers.SerializerMethodField()

    def get_resolved_event(self, obj):
        if obj.resolved_event:
            return MissingHeartbeatDetectionEventSerializer(obj.resolved_event).data
        else:
            return None
