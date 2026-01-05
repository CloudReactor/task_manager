from typing import override

from django_filters import CharFilter
from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter

from ..common.utils import model_class_to_type_string

from ..models import (
    NotificationDeliveryMethod,
    EmailNotificationDeliveryMethod,
    PagerDutyNotificationDeliveryMethod
)
from ..serializers import (
    NotificationDeliveryMethodSerializer,
    EmailNotificationDeliveryMethodSerializer,
    PagerDutyNotificationDeliveryMethodSerializer
)

from .base_view_set import BaseViewSet
from .atomic_viewsets import AtomicModelViewSet


class NotificationDeliveryMethodFilter(filters.FilterSet):
    name = CharFilter()
    created_by_group__id = NumberFilter()
    run_environment__uuid = CharFilter()

    class Meta:
        model = NotificationDeliveryMethod
        fields = ['name', 'created_by_group__id', 'run_environment__uuid']


class NotificationDeliveryMethodViewSet(AtomicModelViewSet, BaseViewSet):
    model_class = NotificationDeliveryMethod
    serializer_class = NotificationDeliveryMethodSerializer
    filterset_class = NotificationDeliveryMethodFilter
    search_fields = ('uuid', 'name', 'description',)
    ordering_fields = ('uuid', 'name', 'run_environment__name',)

    # Compute type string to serializer mapping once at class definition time
    _type_to_serializer = {
        model_class_to_type_string(EmailNotificationDeliveryMethod): EmailNotificationDeliveryMethodSerializer,
        model_class_to_type_string(PagerDutyNotificationDeliveryMethod): PagerDutyNotificationDeliveryMethodSerializer,
    }

    @override
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the delivery method subtype.
        For create operations, checks the request data for delivery_method_type.
        For update/retrieve operations, checks the instance type.
        """
        # For create actions, check request data for delivery_method_type
        if self.action == 'create' and self.request:
            delivery_method_type = self.request.data.get('delivery_method_type')
            if delivery_method_type in self._type_to_serializer:
                return self._type_to_serializer[delivery_method_type]

        # For update/retrieve actions, check the instance type
        if self.action in ('retrieve', 'update', 'partial_update', 'destroy'):
            try:
                obj = self.get_object()
                if isinstance(obj, EmailNotificationDeliveryMethod):
                    return EmailNotificationDeliveryMethodSerializer
                elif isinstance(obj, PagerDutyNotificationDeliveryMethod):
                    return PagerDutyNotificationDeliveryMethodSerializer
            except Exception:
                # Object doesn't exist or permission denied
                pass

        # Default to base serializer
        return NotificationDeliveryMethodSerializer
