from typing import TYPE_CHECKING

import uuid

from django.db import models

from .event import Event

from .alert_send_status import AlertSendStatus

if TYPE_CHECKING:
    from .notification_profile import NotificationProfile
    from .notification_delivery_method import NotificationDeliveryMethod


class Notification(models.Model):
    MAX_SEND_RESULT_LENGTH = 50000

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    notification_profile = models.ForeignKey('NotificationProfile', on_delete=models.CASCADE)
    notification_delivery_method = models.ForeignKey('NotificationDeliveryMethod', on_delete=models.CASCADE)
    attempted_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    send_status = models.IntegerField(null=True, blank=True, default=AlertSendStatus.SENDING)
    send_result = models.JSONField(blank=True, null=True)
