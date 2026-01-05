import logging
from typing import override

from rest_framework import serializers

from ..models import NotificationDeliveryMethod, Event
from ..common.utils import model_class_to_type_string
from .embedded_id_validating_serializer_mixin import EmbeddedIdValidatingSerializerMixin
from .group_serializer import GroupSerializer
from .group_setting_serializer_mixin import GroupSettingSerializerMixin
from .event_serializer import EventSeveritySerializer
from .serializer_helpers import SerializerHelpers


logger = logging.getLogger(__name__)


class RateLimitTierSerializer(serializers.Serializer):
    max_requests_per_period = serializers.IntegerField(allow_null=True)
    request_period_seconds = serializers.IntegerField(allow_null=True)
    max_severity = EventSeveritySerializer(allow_null=True)
    request_period_started_at = serializers.DateTimeField(allow_null=True)
    request_count_in_period = serializers.IntegerField(allow_null=True)


class NotificationDeliveryMethodSerializer(GroupSettingSerializerMixin,
    EmbeddedIdValidatingSerializerMixin,
    serializers.HyperlinkedModelSerializer, SerializerHelpers):
    """
    Serializer for NotificationDeliveryMethod that exposes rate limit tiers
    as an array under the `rate_limit_tiers` property.
    """

    url = serializers.HyperlinkedIdentityField(
        view_name='notification_delivery_methods-detail', lookup_field='uuid')

    created_by_group = GroupSerializer(read_only=True, include_users=False)

    delivery_method_type = serializers.SerializerMethodField()
    rate_limit_tiers = serializers.SerializerMethodField()

    class Meta:
        model = NotificationDeliveryMethod
        fields = [
            'url', 'uuid', 'name', 'description', 'dashboard_url',
            'run_environment', 'delivery_method_type', 'rate_limit_tiers',
            'created_by_user', 'created_by_group', 'created_at', 'updated_at'
        ]

        read_only_fields = [
            'url', 'uuid', 'dashboard_url', 'created_by_user',
            'created_by_group', 'created_at', 'updated_at'
        ]

    def get_delivery_method_type(self, obj: NotificationDeliveryMethod) -> str:
        # Return the concrete Python subclass name converted to snake_case
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
        from .email_notification_delivery_method_serializer import EmailNotificationDeliveryMethodSerializer
        from .pagerduty_notification_delivery_method_serializer import PagerDutyNotificationDeliveryMethodSerializer
        from ..models import EmailNotificationDeliveryMethod, PagerDutyNotificationDeliveryMethod

        # Check instance type and delegate to appropriate serializer
        # Pass flag in context to prevent infinite recursion
        child_context = {**self.context, SerializerHelpers.SKIP_POLYMORPHIC_DELEGATION: True}

        if isinstance(instance, EmailNotificationDeliveryMethod):
            serializer = EmailNotificationDeliveryMethodSerializer(instance, context=child_context)
            return serializer.data
        elif isinstance(instance, PagerDutyNotificationDeliveryMethod):
            serializer = PagerDutyNotificationDeliveryMethodSerializer(instance, context=child_context)
            return serializer.data

        # Default: use parent's to_representation for base NotificationDeliveryMethod
        return super().to_representation(instance)

    def get_rate_limit_tiers(self, ndm: NotificationDeliveryMethod) -> list[dict[str, any]]:
        tiers = []
        # Use EventSeveritySerializer to produce string labels for severities
        severity_serializer = EventSeveritySerializer()

        for i in range(NotificationDeliveryMethod.MAX_RATE_LIMIT_TIERS):
            numeric = getattr(ndm, f'max_severity_{i}')
            if numeric is None:
                severity_label = None
            else:
                severity_label = severity_serializer.to_representation(numeric)

            tier = {
                'max_requests_per_period': getattr(ndm, f'max_requests_per_period_{i}'),
                'request_period_seconds': getattr(ndm, f'request_period_seconds_{i}'),
                'max_severity': severity_label,
                'request_period_started_at': getattr(ndm, f'request_period_started_at_{i}'),
                'request_count_in_period': getattr(ndm, f'request_count_in_period_{i}'),
            }

            tiers.append(tier)

        return tiers
