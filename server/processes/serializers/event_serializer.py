import logging
from typing import override

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from ..models import Event
from ..common.utils import model_class_to_type_string
from .name_and_uuid_serializer import NameAndUuidSerializer
from .group_serializer import GroupSerializer
from .serializer_helpers import SerializerHelpers
from django.utils.text import camel_case_to_spaces

logger = logging.getLogger(__name__)


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


class EventSerializer(serializers.HyperlinkedModelSerializer, SerializerHelpers):
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
            'url', 'uuid', 'event_at', 'detected_at',
            'severity', 'event_type',
            'error_summary', 'error_details_message',
            'source', 'details', 'grouping_key',
            'resolved_at', 'resolved_event', 'created_by_group',
        ]

    def get_event_type(self, obj: Event) -> str:
        return model_class_to_type_string(obj.__class__)

    @override
    def to_representation(self, instance):
        """
        Dynamically delegate to the appropriate child serializer based on instance type.
        This ensures list views use the correct serializer per object.
        """
        # Check if we should skip delegation (to avoid infinite recursion)
        if self.context.get(SerializerHelpers.SKIP_POLYMORPHIC_DELEGATION):
            return super().to_representation(instance)

        # Import here to avoid circular import issues
        from .execution_status_change_event_serializer import ExecutionStatusChangeEventSerializer
        from .task_execution_status_change_event_serializer import TaskExecutionStatusChangeEventSerializer
        from .workflow_execution_status_change_event_serializer import WorkflowExecutionStatusChangeEventSerializer
        from ..models import (
            ExecutionStatusChangeEvent,
            TaskExecutionStatusChangeEvent,
            WorkflowExecutionStatusChangeEvent
        )

        # Check instance type and delegate to appropriate serializer
        # Pass flag in context to prevent infinite recursion
        child_context = {**self.context, SerializerHelpers.SKIP_POLYMORPHIC_DELEGATION: True}

        # Check most specific types first
        if isinstance(instance, TaskExecutionStatusChangeEvent):
            serializer = TaskExecutionStatusChangeEventSerializer(instance, context=child_context)
            return serializer.data
        elif isinstance(instance, WorkflowExecutionStatusChangeEvent):
            serializer = WorkflowExecutionStatusChangeEventSerializer(instance, context=child_context)
            return serializer.data
        elif isinstance(instance, ExecutionStatusChangeEvent):
            serializer = ExecutionStatusChangeEventSerializer(instance, context=child_context)
            return serializer.data

        # Default: use parent's to_representation for base Event
        return super().to_representation(instance)
