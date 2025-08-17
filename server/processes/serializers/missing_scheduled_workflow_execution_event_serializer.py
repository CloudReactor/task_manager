import logging

from rest_framework import serializers

from ..models import MissingScheduledWorkflowExecutionEvent
from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers

logger = logging.getLogger(__name__)


class MissingScheduledWorkflowExecutionEventSerializer(serializers.ModelSerializer,
        SerializerHelpers):
    class Meta:
        model = MissingScheduledWorkflowExecutionEvent
        fields = ('uuid', 'workflow', 'schedule', 'expected_execution_at',
                  'detected_at', 'resolved_at')

    task = NameAndUuidSerializer(view_name='events-detail')
