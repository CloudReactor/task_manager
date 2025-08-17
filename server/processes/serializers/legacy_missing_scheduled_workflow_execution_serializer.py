import logging

from rest_framework import serializers

from processes.models import LegacyMissingScheduledWorkflowExecution
from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers

logger = logging.getLogger(__name__)


class LegacyMissingScheduledWorkflowExecutionSerializer(serializers.ModelSerializer,
                                                        SerializerHelpers):
    """
    Represents an event that is created when CloudReactor detects that
    a scheduled Workflow did not run when it was expected.
    """

    class Meta:
        model = LegacyMissingScheduledWorkflowExecution
        fields = ('uuid', 'workflow', 'schedule', 'expected_execution_at',
                  'detected_at', 'resolved_at')

    workflow = NameAndUuidSerializer(view_name='workflows-detail')
