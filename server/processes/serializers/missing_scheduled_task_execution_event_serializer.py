import logging

from ..models import MissingScheduledTaskExecutionEvent
from .name_and_uuid_serializer import NameAndUuidSerializer
from .event_serializer import EventSerializer

logger = logging.getLogger(__name__)


class MissingScheduledTaskExecutionEventSerializer(EventSerializer):
    task = NameAndUuidSerializer(view_name='tasks-detail', required=False)

    class Meta(EventSerializer.Meta):
        model = MissingScheduledTaskExecutionEvent
        fields = EventSerializer.Meta.fields + [
            'task',
            'schedule',
            'expected_execution_at',
        ]

