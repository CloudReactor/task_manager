from typing import override

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from ..models import Notification
from ..models.notification_send_status import NotificationSendStatus
from .event_serializer import EventSeveritySerializer
from .name_and_uuid_serializer import NameAndUuidSerializer
from .group_serializer import GroupSerializer


@extend_schema_field(field=serializers.ChoiceField(choices=[
        status.name for status in list(NotificationSendStatus)
    ]), component_name='NotificationSendStatus')
class NotificationSendStatusSerializer(serializers.BaseSerializer):
    @override
    def to_representation(self, instance) -> str | None:
        if instance is None:
            return None

        return NotificationSendStatus(instance).name

    @override
    def to_internal_value(self, data) -> int | None:
        if data is None:
            return None

        if isinstance(data, str):
            return NotificationSendStatus[data.strip().upper()].value

        raise serializers.ValidationError('Invalid send status')


class NotificationSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for Notification model.
    Tracks notification delivery attempts with status, results, and rate limiting info.
    """

    url = serializers.HyperlinkedIdentityField(view_name='notifications-detail', lookup_field='uuid')

    event = NameAndUuidSerializer(view_name='events-detail', required=False)
    notification_profile = NameAndUuidSerializer(view_name='notification_profiles-detail', required=False)
    notification_delivery_method = NameAndUuidSerializer(view_name='notification_delivery_methods-detail', required=False)
    send_status = NotificationSendStatusSerializer(required=False, allow_null=True)
    rate_limit_max_severity = EventSeveritySerializer(required=False, allow_null=True)
    created_by_group = GroupSerializer(read_only=True, include_users=False)

    class Meta:
        model = Notification
        fields = [
            'url', 'uuid',
            'event', 'notification_profile', 'notification_delivery_method',
            'attempted_at', 'completed_at',
            'send_status', 'send_result',
            'exception_type', 'exception_message',
            'rate_limit_max_requests_per_period',
            'rate_limit_request_period_seconds',
            'rate_limit_max_severity',
            'rate_limit_tier_index',
            'created_by_group',
            'created_at', 'updated_at', 'dashboard_url',
        ]

        read_only_fields = [
            'url', 'uuid', 'created_by_group',
            'created_at', 'updated_at', 'dashboard_url',
        ]
