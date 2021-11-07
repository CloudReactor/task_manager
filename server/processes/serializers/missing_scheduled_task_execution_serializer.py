import logging

from rest_framework import serializers

from processes.models import MissingScheduledTaskExecution
from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers

logger = logging.getLogger(__name__)


class MissingScheduledTaskExecutionSerializer(serializers.ModelSerializer,
        SerializerHelpers):
    """
    Represents an event that is created when CloudReactor detects that
    a scheduled Task did not run when it was expected.
    """

    class Meta:
        model = MissingScheduledTaskExecution
        fields = ('uuid', 'task', 'schedule', 'expected_execution_at',
                  'detected_at', 'resolved_at')

    task = NameAndUuidSerializer(view_name='tasks-detail')
