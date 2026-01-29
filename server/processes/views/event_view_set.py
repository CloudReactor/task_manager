import logging
from typing import override
from urllib.request import Request

from django.views import View

from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter

from rest_framework import permissions

from processes.common.request_helpers import required_user_and_group_from_request
from processes.models.user_group_access_level import UserGroupAccessLevel

from ..permissions import IsCreatedByGroup

from ..common.utils import model_class_to_type_string

from ..models import (
    BasicEvent,
    Event,
    InsufficientServiceTaskExecutionsEvent,
    MissingHeartbeatDetectionEvent,
    MissingScheduledTaskExecutionEvent,
    MissingScheduledWorkflowExecutionEvent,
    RunEnvironment,
    TaskExecutionStatusChangeEvent,
    WorkflowExecutionStatusChangeEvent
)
from ..serializers import *

from .base_view_set import BaseViewSet
from .atomic_viewsets import AtomicModelViewSet


logger = logging.getLogger(__name__)


class EventPermission(IsCreatedByGroup):
    @override
    def required_access_level_for_mutation(self, request: Request, view: View,
            obj: object) -> int | None:        
        return UserGroupAccessLevel.ACCESS_LEVEL_TASK


class EventFilter(filters.FilterSet):
    created_by_group__id = NumberFilter()

    # CHECKME: should this be a ChoiceFilter?
    severity = NumberFilter()

    class Meta:
        model = Event
        fields = ['created_by_group__id', 'severity']


class EventViewSet(AtomicModelViewSet, BaseViewSet):
    model_class = Event
    serializer_class = EventSerializer
    permission_classes = (permissions.IsAuthenticated, EventPermission,)
    filterset_class = EventFilter
    search_fields = ('uuid', 'error_summary', 'source',)
    ordering_fields = ('event_at', 'detected_at', 'severity',)
    ordering = '-event_at'  # Default ordering by event timestamp, newest first

    # Compute type string to serializer mapping once at class definition time
    _type_to_serializer = {
        model_class_to_type_string(BasicEvent): BasicEventSerializer,
        model_class_to_type_string(TaskExecutionStatusChangeEvent): TaskExecutionStatusChangeEventSerializer,
        model_class_to_type_string(WorkflowExecutionStatusChangeEvent): WorkflowExecutionStatusChangeEventSerializer,
        model_class_to_type_string(MissingHeartbeatDetectionEvent): MissingHeartbeatDetectionEventSerializer,
        model_class_to_type_string(MissingScheduledTaskExecutionEvent): MissingScheduledTaskExecutionEventSerializer,
        model_class_to_type_string(MissingScheduledWorkflowExecutionEvent): MissingScheduledWorkflowExecutionEventSerializer,
        model_class_to_type_string(InsufficientServiceTaskExecutionsEvent): InsufficientServiceTaskExecutionsEventSerializer,
    }


    # CHECKME: is this needed?
    @override
    def get_queryset_for_all_groups(self):
        """Override to avoid ordering groups by event_at"""
        return self.model_class.objects.filter(
            created_by_group__in=self.request.user.groups.all())

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
        if self.action in ('retrieve', 'update', 'partial_update'):
            try:
                obj = self.get_object()
                # Check most specific types first
                if isinstance(obj, BasicEvent):
                    return BasicEventSerializer
                elif isinstance(obj, TaskExecutionStatusChangeEvent):
                    return TaskExecutionStatusChangeEventSerializer
                elif isinstance(obj, WorkflowExecutionStatusChangeEvent):
                    return WorkflowExecutionStatusChangeEventSerializer
                elif isinstance(obj, MissingHeartbeatDetectionEvent):
                    return MissingHeartbeatDetectionEventSerializer
                elif isinstance(obj, MissingScheduledTaskExecutionEvent):
                    return MissingScheduledTaskExecutionEventSerializer
                elif isinstance(obj, MissingScheduledWorkflowExecutionEvent):
                    return MissingScheduledWorkflowExecutionEventSerializer
                elif isinstance(obj, InsufficientServiceTaskExecutionsEvent):
                    return InsufficientServiceTaskExecutionsEventSerializer
            except Exception:
                # Object doesn't exist or permission denied
                pass

        # Default to base serializer
        return EventSerializer
