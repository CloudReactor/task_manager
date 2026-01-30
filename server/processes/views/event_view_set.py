import logging
from typing import override
from urllib.request import Request

from django.db.models import Q
from django.views import View

from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter, CharFilter

from rest_framework import permissions

from processes.common.request_helpers import required_user_and_group_from_request
from processes.models.user_group_access_level import UserGroupAccessLevel

from ..permissions import IsCreatedByGroup

from ..common.utils import model_class_to_type_string

from ..models import (
    Event,
    RunEnvironment,
)
from ..serializers import EventSerializer

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

    severity = CharFilter(method='filter_severity')

    def filter_severity(self, queryset, name, value):
        """
        Filter severity by label (e.g., 'error', 'warning') or numeric value.
        Accepts severity labels like 'error', 'warning', 'info', etc. (case-insensitive)
        or numeric values.
        """
        if not value:
            return queryset
        
        # Try to parse as integer first
        try:
            severity_int = int(value)
            return queryset.filter(severity=severity_int)
        except ValueError:
            pass
        
        # Try to parse as severity label
        try:
            severity_enum = Event.Severity[value.upper()]
            return queryset.filter(severity=severity_enum.value)
        except KeyError:
            # Invalid severity label, return empty queryset
            logger.warning(f"Invalid severity filter value: {value}")
            return queryset.none()

    class Meta:
        model = Event
        fields = {
            'created_by_group__id': ['exact'],
            'run_environment__uuid': ['exact', 'in'],
        }


class EventViewSet(AtomicModelViewSet, BaseViewSet):
    model_class = Event
    serializer_class = EventSerializer
    permission_classes = (permissions.IsAuthenticated, EventPermission,)
    filterset_class = EventFilter
    search_fields = ('uuid', 'error_summary', 'source',)
    ordering_fields = ('event_at', 'detected_at', 'severity',)
    ordering = '-event_at'  # Default ordering by event timestamp, newest first

    # Cache for type string to serializer mapping
    _type_string_to_serializer_cache = None

    @classmethod
    def _get_type_string_to_serializer_map(cls):
        """Build mapping from event_type strings to serializer classes using EventSerializer's mapping."""
        if cls._type_string_to_serializer_cache is None:
            type_map = EventSerializer._get_type_to_serializer_map()
            
            # Convert to type_string-to-serializer mapping
            cls._type_string_to_serializer_cache = {
                model_class_to_type_string(model_class): serializer_class
                for model_class, serializer_class in type_map.items()
            }
        return cls._type_string_to_serializer_cache

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
            type_string_map = self._get_type_string_to_serializer_map()
            if event_type in type_string_map:
                return type_string_map[event_type]

        # For update/retrieve actions, check the instance type
        if self.action in ('retrieve', 'update', 'partial_update'):
            try:
                obj = self.get_object()
                # Use EventSerializer's type-to-serializer mapping
                type_map = EventSerializer._get_type_to_serializer_map()
                serializer_class = type_map.get(type(obj))
                if serializer_class:
                    return serializer_class
            except Exception:
                # Object doesn't exist or permission denied
                pass

        # Default to base serializer
        return EventSerializer
