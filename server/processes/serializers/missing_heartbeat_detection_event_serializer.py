import logging

from ..models import MissingHeartbeatDetectionEvent
from .name_and_uuid_serializer import NameAndUuidSerializer
from .event_serializer import EventSerializer

logger = logging.getLogger(__name__)


class MissingHeartbeatDetectionEventSerializer(EventSerializer):
    """
    Serializer for MissingHeartbeatDetectionEvent.
    Includes heartbeat timing information and Task Execution reference.
    """

    task = NameAndUuidSerializer(view_name='tasks-detail', required=False)
    task_execution = NameAndUuidSerializer(view_name='task_executions-detail', required=False)

    class Meta(EventSerializer.Meta):
        model = MissingHeartbeatDetectionEvent
        fields = EventSerializer.Meta.fields + [
            'task',
            'task_execution',
            'last_heartbeat_at',
            'expected_heartbeat_at',
            'heartbeat_interval_seconds',
        ]
