from django_filters import CharFilter
from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter

from ..models import Notification
from ..serializers import NotificationSerializer

from .base_view_set import BaseViewSet
from .atomic_viewsets import AtomicModelViewSet


class NotificationFilter(filters.FilterSet):
    created_by_group__id = NumberFilter()
    event__uuid = CharFilter()
    notification_profile__uuid = CharFilter()
    notification_delivery_method__uuid = CharFilter()
    send_status = NumberFilter()

    class Meta:
        model = Notification
        fields = ['created_by_group__id', 'event__uuid', 'notification_profile__uuid',
                  'notification_delivery_method__uuid', 'send_status']


class NotificationViewSet(AtomicModelViewSet, BaseViewSet):
    model_class = Notification
    serializer_class = NotificationSerializer
    filterset_class = NotificationFilter
    search_fields = ('uuid', 'exception_type', 'exception_message',)
    ordering_fields = ('uuid', 'attempted_at', 'completed_at', 'send_status',)
