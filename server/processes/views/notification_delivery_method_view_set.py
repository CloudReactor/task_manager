from typing import override

import logging

from django.core.exceptions import ObjectDoesNotExist

from django_filters import CharFilter
from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from ..models import (
    NotificationDeliveryMethod,
    EmailNotificationDeliveryMethod,
    PagerDutyNotificationDeliveryMethod,
    AppriseNotificationDeliveryMethod,
    BasicEvent,
    UserGroupAccessLevel,
)
from ..serializers import (
    NotificationDeliveryMethodSerializer,
    EmailNotificationDeliveryMethodSerializer,
    PagerDutyNotificationDeliveryMethodSerializer,
    AppriseNotificationDeliveryMethodSerializer,
)
from ..common.request_helpers import (
    ensure_group_access_level,
    required_user_and_group_from_request,
)

from .base_view_set import BaseViewSet
from .atomic_viewsets import AtomicModelViewSet
from .cloning_mixin import CloningMixin

logger = logging.getLogger(__name__)


class NotificationDeliveryMethodFilter(filters.FilterSet):
    name = CharFilter()
    created_by_group__id = NumberFilter()
    run_environment__uuid = CharFilter()

    class Meta:
        model = NotificationDeliveryMethod
        fields = ['name', 'created_by_group__id', 'run_environment__uuid']


class NotificationDeliveryMethodViewSet(AtomicModelViewSet, CloningMixin, BaseViewSet):
    model_class = NotificationDeliveryMethod
    serializer_class = NotificationDeliveryMethodSerializer
    filterset_class = NotificationDeliveryMethodFilter
    search_fields = ('uuid', 'name', 'description',)
    ordering_fields = ('uuid', 'name', 'run_environment__name',)

    # Map simplified type strings to serializer classes
    # These match the values returned by get_delivery_method_type()
    _type_to_serializer = {
        'email': EmailNotificationDeliveryMethodSerializer,
        'pager_duty': PagerDutyNotificationDeliveryMethodSerializer,
        'apprise': AppriseNotificationDeliveryMethodSerializer,
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
        try:
            obj = self.get_object()
            if isinstance(obj, EmailNotificationDeliveryMethod):
                return EmailNotificationDeliveryMethodSerializer
            elif isinstance(obj, PagerDutyNotificationDeliveryMethod):
                return PagerDutyNotificationDeliveryMethodSerializer
            elif isinstance(obj, AppriseNotificationDeliveryMethod):
                return AppriseNotificationDeliveryMethodSerializer
        except Exception:
            # Object doesn't exist or permission denied
            pass

        # Default to base serializer
        return NotificationDeliveryMethodSerializer

    @action(methods=['post'], detail=True,
            url_path='test_event', url_name='test_event')
    def test_event(self, request: Request, uuid: str):
        try:
            method = self.model_objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound(detail="Resource not found")

        _user, group = required_user_and_group_from_request(request=request)[:2]

        ensure_group_access_level(group=method.created_by_group,
            min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            run_environment=getattr(method, 'run_environment', None),
            allow_api_key=True, request=request)

        event = BasicEvent(
            severity=BasicEvent.Severity.INFO,
            error_summary=f"Test event from Notification Delivery Method '{method.name}'",
            source=BasicEvent.SOURCE_SYSTEM,
            created_by_group=method.created_by_group,
            run_environment=getattr(method, 'run_environment', None),
        )
        event.save()

        try:
            result = method.send(event)
        except Exception as ex:
            logger.warning(f"test_event send failed for {method.uuid}: {ex}")
            return Response(
                {'error': str(ex)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        return Response(
            {'event_uuid': str(event.uuid), 'result': result},
            status=status.HTTP_200_OK
        )
