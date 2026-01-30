from ..models import PagerDutyNotificationDeliveryMethod
from .notification_delivery_method_serializer import NotificationDeliveryMethodSerializer


class PagerDutyNotificationDeliveryMethodSerializer(NotificationDeliveryMethodSerializer):
    """
    Serializer for PagerDutyNotificationDeliveryMethod.
    Includes PagerDuty-specific fields (API key and event templates) in addition
    to the base NotificationDeliveryMethod fields and rate_limit_tiers.
    """

    class Meta(NotificationDeliveryMethodSerializer.Meta):
        model = PagerDutyNotificationDeliveryMethod
        fields = NotificationDeliveryMethodSerializer.Meta.fields + [
            'pagerduty_api_key',
            'pagerduty_event_class_template',
            'pagerduty_event_component_template',
            'pagerduty_event_group_template',
        ]
        read_only_fields = NotificationDeliveryMethodSerializer.Meta.read_only_fields
