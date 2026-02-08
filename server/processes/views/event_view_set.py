import logging
from typing import override
from urllib.request import Request

from django.db.models import Q, F, Value
from django.db.models.functions import Coalesce
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

    # Filter by event_type strings (as returned by the API, e.g. 'basic_event',
    # 'execution_status_change_event'). Accepts comma-separated list.
    event_type = CharFilter(method='filter_event_type')

    severity = CharFilter(method='filter_severity')
    min_severity = CharFilter(method='filter_min_severity')
    max_severity = CharFilter(method='filter_max_severity')

    # Filter by acknowledgement status: 'acknowledged', 'not_acknowledged', or empty for any
    acknowledged_status = CharFilter(method='filter_acknowledged_status')

    # Filter by resolved status: 'resolved', 'not_resolved', or empty for any
    resolved_status = CharFilter(method='filter_resolved_status')

    def _parse_severity_value(self, value):
        """
        Parse a severity value which can be either a label or numeric value.
        Returns the numeric severity value or None if invalid.
        """
        # Try to parse as integer first
        try:
            return int(value)
        except ValueError:
            pass

        # Try to parse as severity label
        try:
            severity_enum = Event.Severity[value.upper()]
            return severity_enum.value
        except KeyError:
            logger.warning(f"Invalid severity value: {value}")
            return None

    def filter_severity(self, queryset, name, value):
        """
        Filter severity by label (e.g., 'error', 'warning') or numeric value.
        Accepts comma-separated list of severity labels/values or single value.
        """
        if not value:
            return queryset

        # Check if it's a comma-separated list
        if ',' in value:
            values = [v.strip() for v in value.split(',')]
            severity_ints = []
            for v in values:
                severity_int = self._parse_severity_value(v)
                if severity_int is not None:
                    severity_ints.append(severity_int)

            if severity_ints:
                return queryset.filter(severity__in=severity_ints)
            else:
                return queryset.none()
        else:
            # Single value
            severity_int = self._parse_severity_value(value)
            if severity_int is not None:
                return queryset.filter(severity=severity_int)
            else:
                return queryset.none()

    def filter_min_severity(self, queryset, name, value):
        """
        Filter events with severity greater than or equal to the specified value.
        Accepts severity label or numeric value.
        """
        if not value:
            return queryset

        severity_int = self._parse_severity_value(value)
        if severity_int is not None:
            return queryset.filter(severity__gte=severity_int)
        else:
            return queryset.none()

    def filter_max_severity(self, queryset, name, value):
        """
        Filter events with severity less than or equal to the specified value.
        Accepts severity label or numeric value.
        """
        if not value:
            return queryset

        severity_int = self._parse_severity_value(value)
        if severity_int is not None:
            return queryset.filter(severity__lte=severity_int)
        else:
            return queryset.none()

    def filter_event_type(self, queryset, name, value):
        """
        Filter events by event_type strings (as returned by `EventSerializer.get_event_type`).
        Accepts a single value or a comma-separated list of type strings.
        Maps the incoming type string(s) to the underlying TypedModel `type` values
        and filters the queryset by the `type` column.
        """
        if not value:
            return queryset

        # Support comma-separated lists
        event_types = [v for v in value.split(',')] if ',' in value else [value]

        type_names = ["processes." + value.strip().replace("_", "") + "event" for value in event_types]

        if not type_names:
            # No matching types; return empty queryset
            return queryset.none()

        return queryset.filter(type__in=type_names)

    def filter_acknowledged_status(self, queryset, name, value):
        """
        Filter events by acknowledgement status.
        - 'acknowledged': events that have been acknowledged (acknowledged_at is not null)
        - 'not_acknowledged': events that have not been acknowledged (acknowledged_at is null)
        - empty or other values: no filtering
        """
        if not value:
            return queryset

        if value == 'acknowledged':
            return queryset.filter(acknowledged_at__isnull=False)
        elif value == 'not_acknowledged':
            return queryset.filter(acknowledged_at__isnull=True)
        else:
            # Invalid value, return empty queryset
            return queryset.none()

    def filter_resolved_status(self, queryset, name, value):
        """
        Filter events by resolved status.
        - 'resolved': events that have been resolved (resolved_at is not null)
        - 'not_resolved': events that have not been resolved (resolved_at is null)
        - empty or other values: no filtering
        """
        if not value:
            return queryset

        if value == 'resolved':
            return queryset.filter(resolved_at__isnull=False)
        elif value == 'not_resolved':
            return queryset.filter(resolved_at__isnull=True)
        else:
            # Invalid value, return empty queryset
            return queryset.none()

    class Meta:
        model = Event
        fields = {
            'created_by_group__id': ['exact'],
            'run_environment__uuid': ['exact', 'in'],
            'grouping_key': ['exact'],
            'task__uuid': ['exact'],
            'workflow__uuid': ['exact'],
            'task_execution__uuid': ['exact'],
            'workflow_execution__uuid': ['exact'],            
        }


class EventViewSet(AtomicModelViewSet, BaseViewSet):
    model_class = Event
    serializer_class = EventSerializer
    permission_classes = (permissions.IsAuthenticated, EventPermission,)
    filterset_class = EventFilter
    search_fields = ('uuid', 'error_summary', 'source',)
    ordering_fields = (
        'event_at', 'type', 'severity', 'run_environment__name',
        'detected_at', 'resolved_at', 'acknowledged_at',
        'executable__name'
    )
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

    @override
    def get_queryset(self):
        """Override to annotate executable__name using COALESCE of task__name and workflow__name."""
        queryset = super().get_queryset()
        
        # Annotate the queryset with executable__name that coalesces task__name and workflow__name
        # This allows ordering by either task or workflow name using a single field
        queryset = queryset.annotate(
            executable__name=Coalesce(F('task__name'), F('workflow__name'), Value(''))
        )
        
        return queryset

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
