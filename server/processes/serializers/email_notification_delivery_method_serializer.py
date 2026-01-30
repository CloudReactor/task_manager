from rest_framework import serializers

from ..models import EmailNotificationDeliveryMethod
from .notification_delivery_method_serializer import NotificationDeliveryMethodSerializer


class EmailNotificationDeliveryMethodSerializer(NotificationDeliveryMethodSerializer):
    """
    Serializer for EmailNotificationDeliveryMethod.
    Includes email address fields (to, cc, bcc) in addition to the base
    NotificationDeliveryMethod fields and rate_limit_tiers.
    """

    class Meta(NotificationDeliveryMethodSerializer.Meta):
        model = EmailNotificationDeliveryMethod
        fields = NotificationDeliveryMethodSerializer.Meta.fields + [
            'email_to_addresses',
            'email_cc_addresses',
            'email_bcc_addresses',
        ]
        read_only_fields = NotificationDeliveryMethodSerializer.Meta.read_only_fields
