import logging

from rest_framework import serializers

from processes.models import MissingScheduledWorkflowExecution
from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers

logger = logging.getLogger(__name__)


class MissingScheduledWorkflowExecutionSerializer(serializers.ModelSerializer,
                                                  SerializerHelpers):
    class Meta:
        model = MissingScheduledWorkflowExecution
        fields = ('uuid', 'workflow', 'schedule', 'expected_execution_at',
                  'detected_at', 'resolved_at')

    workflow = NameAndUuidSerializer(view_name='workflows-detail',
        read_only=True)
