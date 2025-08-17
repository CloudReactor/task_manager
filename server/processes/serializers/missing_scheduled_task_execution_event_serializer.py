import logging

from rest_framework import serializers

from ..models import MissingScheduledTaskExecutionEvent
from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers

logger = logging.getLogger(__name__)


class MissingScheduledTaskExecutionEventSerializer(serializers.ModelSerializer,
        SerializerHelpers):
    class Meta:
        model = MissingScheduledTaskExecutionEvent
        fields = ('uuid', 'task', 'schedule', 'expected_execution_at',
                  'detected_at', 'resolved_at')

    task = NameAndUuidSerializer(view_name='events-detail')
