import logging

from ..models import MissingScheduledWorkflowExecutionEvent
from .name_and_uuid_serializer import NameAndUuidSerializer
from .event_serializer import EventSerializer

logger = logging.getLogger(__name__)


class MissingScheduledWorkflowExecutionEventSerializer(EventSerializer):
    workflow = NameAndUuidSerializer(view_name='workflows-detail', required=False)

    class Meta(EventSerializer.Meta):
        model = MissingScheduledWorkflowExecutionEvent
        fields = EventSerializer.Meta.fields + [
            'workflow',
            'schedule',
            'expected_execution_at',
        ]
