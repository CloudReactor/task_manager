from ..models import AppriseNotificationDeliveryMethod
from .notification_delivery_method_serializer import NotificationDeliveryMethodSerializer


class AppriseNotificationDeliveryMethodSerializer(NotificationDeliveryMethodSerializer):
    """
    Serializer for AppriseNotificationDeliveryMethod.
    Includes apprise-specific fields (URL) in addition to the base
    NotificationDeliveryMethod fields and rate_limit_tiers.
    """

    class Meta(NotificationDeliveryMethodSerializer.Meta):
        model = AppriseNotificationDeliveryMethod
        fields = NotificationDeliveryMethodSerializer.Meta.fields + [
            'apprise_url',
        ]
        read_only_fields = NotificationDeliveryMethodSerializer.Meta.read_only_fields
