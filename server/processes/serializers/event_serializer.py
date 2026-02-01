import logging
from typing import Any, override

from django.utils.text import camel_case_to_spaces

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from ..models import Event, UserGroupAccessLevel
from ..common.utils import model_class_to_type_string

from .embedded_id_validating_serializer_mixin import EmbeddedIdValidatingSerializerMixin
from .name_and_uuid_serializer import NameAndUuidSerializer
from .group_serializer import GroupSerializer
from .group_setting_serializer_mixin import GroupSettingSerializerMixin
from .serializer_helpers import SerializerHelpers


logger = logging.getLogger(__name__)


def convert_event_severity_value(data: Any) -> int:
    """Convert data to its corresponding integer value."""
    # Accept None, integer, or string inputs.
    if data is None:
        return Event.Severity.NONE.value

    if isinstance(data, int):
        # Store integer severities as-is per request.
        return data

    if isinstance(data, str):
        s = data.strip()

        # Try mapping by enum name first (case-insensitive)
        try:
            return Event.Severity[s.upper()].value
        except KeyError:
            # Fallback: if client passed a numeric string, parse and use as-is
            try:
                return int(s)
            except ValueError:
                raise serializers.ValidationError(f"Unknown severity: {data}")

    raise serializers.ValidationError('Invalid severity')


@extend_schema_field(field=serializers.ChoiceField(choices=[
        sev.name.lower() for sev in list(Event.Severity)
    ]), component_name='EventSeverity')
class EventSeveritySerializer(serializers.BaseSerializer):
    @override
    def to_representation(self, instance) -> str | None:
        if instance is None:
            instance = Event.Severity.NONE.value

        try:
            sev = Event.Severity(instance)
        except Exception:
            return str(instance)

        return sev.name.lower()

    @override
    def to_internal_value(self, data) -> int:
        return convert_event_severity_value(data)

class EventSerializer(EmbeddedIdValidatingSerializerMixin, GroupSettingSerializerMixin,
    SerializerHelpers, serializers.HyperlinkedModelSerializer):
    """
    Serializer for `Event` model.

    - `severity` is the stored integer value.
    - `severity_label` is a string label derived from the enum (lowercase),
      or `null` when the severity is `NONE`.
    """

    url = serializers.HyperlinkedIdentityField(view_name='events-detail', lookup_field='uuid')

    # Serialize severity as a string label (e.g. 'error', 'warning')
    severity = EventSeveritySerializer()
    event_type = serializers.SerializerMethodField()
    resolved_event = NameAndUuidSerializer(view_name='events-detail', required=False)
    created_by_group = GroupSerializer(read_only=True, include_users=False)

    class Meta:
        model = Event
        fields = [
            'url', 'uuid', 'created_by_group', 'created_by_user',
            'run_environment',
            'event_at', 'detected_at',
            'severity', 'event_type',
            'error_summary', 'error_details_message',
            'source', 'details', 'grouping_key',
            'resolved_at', 'resolved_event',
        ]
        read_only_fields = [
            'url', 'uuid', 'created_by_user', 'created_at', 'updated_at',
            'event_type',
        ]

    def get_event_type(self, obj: Event) -> str:
        return model_class_to_type_string(obj.__class__).removesuffix('_event')

    # Class-level mapping of model types to serializers (most specific first)
    _type_to_serializer_cache = None

    @classmethod
    def _get_type_to_serializer_map(cls):
        """Lazy-load the type-to-serializer mapping to avoid circular imports."""
        if cls._type_to_serializer_cache is None:
            # Import here to avoid circular import issues
            from .basic_event_serializer import BasicEventSerializer
            from .execution_status_change_event_serializer import ExecutionStatusChangeEventSerializer
            from .task_execution_status_change_event_serializer import TaskExecutionStatusChangeEventSerializer
            from .workflow_execution_status_change_event_serializer import WorkflowExecutionStatusChangeEventSerializer
            from .missing_heartbeat_detection_event_serializer import MissingHeartbeatDetectionEventSerializer
            from .missing_scheduled_task_execution_event_serializer import MissingScheduledTaskExecutionEventSerializer
            from .missing_scheduled_workflow_execution_event_serializer import MissingScheduledWorkflowExecutionEventSerializer
            from .insufficient_service_task_executions_event_serializer import InsufficientServiceTaskExecutionsEventSerializer
            from ..models import (
                BasicEvent,
                ExecutionStatusChangeEvent,
                TaskExecutionStatusChangeEvent,
                WorkflowExecutionStatusChangeEvent,
                MissingHeartbeatDetectionEvent,
                MissingScheduledTaskExecutionEvent,
                MissingScheduledWorkflowExecutionEvent,
                InsufficientServiceTaskExecutionsEvent
            )

            # Order matters: most specific types first
            cls._type_to_serializer_cache = {
                TaskExecutionStatusChangeEvent: TaskExecutionStatusChangeEventSerializer,
                WorkflowExecutionStatusChangeEvent: WorkflowExecutionStatusChangeEventSerializer,
                MissingHeartbeatDetectionEvent: MissingHeartbeatDetectionEventSerializer,
                MissingScheduledTaskExecutionEvent: MissingScheduledTaskExecutionEventSerializer,
                MissingScheduledWorkflowExecutionEvent: MissingScheduledWorkflowExecutionEventSerializer,
                InsufficientServiceTaskExecutionsEvent: InsufficientServiceTaskExecutionsEventSerializer,
                BasicEvent: BasicEventSerializer,
                ExecutionStatusChangeEvent: ExecutionStatusChangeEventSerializer,
            }
        return cls._type_to_serializer_cache

    @override
    def to_representation(self, instance):
        """
        Dynamically delegate to the appropriate child serializer based on instance type.
        This ensures list views use the correct serializer per object.
        """
        # Check if we should skip delegation (to avoid infinite recursion)
        if self.context.get(SerializerHelpers.SKIP_POLYMORPHIC_DELEGATION):
            return super().to_representation(instance)

        # Get the type-to-serializer mapping
        type_map = self._get_type_to_serializer_map()

        # Direct lookup using the instance's class
        serializer_class = type_map.get(type(instance))

        if serializer_class:
            # Pass flag in context to prevent infinite recursion
            child_context = {**self.context, SerializerHelpers.SKIP_POLYMORPHIC_DELEGATION: True}
            serializer = serializer_class(instance, context=child_context)
            return serializer.data

        # Default: use parent's to_representation for base Event
        return super().to_representation(instance)

    def required_access_level_for_mutation(self):
        return UserGroupAccessLevel.ACCESS_LEVEL_TASK
