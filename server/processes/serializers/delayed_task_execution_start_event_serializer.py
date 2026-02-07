import logging

from ..models import DelayedTaskExecutionStartEvent
from .name_and_uuid_serializer import NameAndUuidSerializer
from .event_serializer import EventSerializer

logger = logging.getLogger(__name__)


class DelayedTaskExecutionStartEventSerializer(EventSerializer):
    """
    Serializer for DelayedTaskExecutionStartEvent.
    Includes timing information about delayed task execution starts.
    """

    task = NameAndUuidSerializer(view_name='tasks-detail', required=False)
    task_execution = NameAndUuidSerializer(view_name='task_executions-detail', required=False)

    class Meta(EventSerializer.Meta):
        model = DelayedTaskExecutionStartEvent
        fields = EventSerializer.Meta.fields + [
            'task',
            'task_execution',
            'desired_start_at',
            'expected_start_by_deadline',
        ]
