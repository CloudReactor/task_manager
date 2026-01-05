from typing import override

from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter

from ..common.utils import model_class_to_type_string

from ..models import (
    Event,
    ExecutionStatusChangeEvent,
    TaskExecutionStatusChangeEvent,
    WorkflowExecutionStatusChangeEvent
)
from ..serializers import (
    EventSerializer,
    ExecutionStatusChangeEventSerializer,
    TaskExecutionStatusChangeEventSerializer,
    WorkflowExecutionStatusChangeEventSerializer
)

from .base_view_set import BaseViewSet
from .atomic_viewsets import AtomicModelViewSet


class EventFilter(filters.FilterSet):
    created_by_group__id = NumberFilter()
    severity = NumberFilter()

    class Meta:
        model = Event
        fields = ['created_by_group__id', 'severity']


class EventViewSet(AtomicModelViewSet, BaseViewSet):
    model_class = Event
    serializer_class = EventSerializer
    filterset_class = EventFilter
    search_fields = ('uuid', 'error_summary', 'source',)
    ordering_fields = ('uuid', 'event_at', 'detected_at', 'severity',)

    # Compute type string to serializer mapping once at class definition time
    _type_to_serializer = {
        model_class_to_type_string(TaskExecutionStatusChangeEvent): TaskExecutionStatusChangeEventSerializer,
        model_class_to_type_string(WorkflowExecutionStatusChangeEvent): WorkflowExecutionStatusChangeEventSerializer,
        model_class_to_type_string(ExecutionStatusChangeEvent): ExecutionStatusChangeEventSerializer,
    }

    @override
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the event subtype.
        For create operations, checks the request data for event_type.
        For update/retrieve operations, checks the instance type.
        """
        # For create actions, check request data for event_type
        if self.action == 'create' and self.request:
            event_type = self.request.data.get('event_type')
            if event_type in self._type_to_serializer:
                return self._type_to_serializer[event_type]

        # For update/retrieve actions, check the instance type
        if self.action in ('retrieve', 'update', 'partial_update', 'destroy'):
            try:
                obj = self.get_object()
                # Check most specific types first
                if isinstance(obj, TaskExecutionStatusChangeEvent):
                    return TaskExecutionStatusChangeEventSerializer
                elif isinstance(obj, WorkflowExecutionStatusChangeEvent):
                    return WorkflowExecutionStatusChangeEventSerializer
                elif isinstance(obj, ExecutionStatusChangeEvent):
                    return ExecutionStatusChangeEventSerializer
            except Exception:
                # Object doesn't exist or permission denied
                pass

        # Default to base serializer
        return EventSerializer
