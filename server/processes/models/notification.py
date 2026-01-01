import logging
import uuid

from django.db import models

from django.contrib.auth.models import Group

from .event import Event

from .alert_send_status import AlertSendStatus
from .subscription import Subscription


logger = logging.getLogger(__name__)


class Notification(models.Model):
    MAX_SEND_RESULT_LENGTH = 50000
    MAX_EXCEPTION_MESSAGE_LENGTH = 50000

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    notification_profile = models.ForeignKey('NotificationProfile', on_delete=models.CASCADE)
    notification_delivery_method = models.ForeignKey('NotificationDeliveryMethod', on_delete=models.CASCADE)
    attempted_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    send_status = models.IntegerField(null=True, blank=True, default=AlertSendStatus.SENDING)
    send_result = models.JSONField(blank=True, null=True)

    exception_type = models.CharField(max_length=255, null=True, blank=True)
    exception_message = models.CharField(max_length=MAX_EXCEPTION_MESSAGE_LENGTH, null=True, blank=True)

    rate_limit_max_requests_per_period = models.PositiveIntegerField(null=True, blank=True)
    rate_limit_request_period_seconds = models.PositiveIntegerField(null=True, blank=True)
    rate_limit_max_severity = models.PositiveIntegerField(null=True, blank=True)
    rate_limit_tier_index = models.PositiveIntegerField(null=True, blank=True)

    # null=True until we can populate this field for existing notifications
    created_by_group = models.ForeignKey(Group, on_delete=models.CASCADE,
            null=True, editable=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_by_group', 'attempted_at']),
        ]


    def save(self, *args, **kwargs) -> None:
        logger.info(f"pre-save with Notification {self.uuid}, {self._state.adding=}, {self.created_by_group=}")

        if (self.created_by_group is None) and self.event:
            self.created_by_group = self.event.created_by_group

        # https://stackoverflow.com/questions/2037320/what-is-the-canonical-way-to-find-out-if-a-django-model-is-saved-to-db
        if self._state.adding:
            group = self.created_by_group

            if group is None:
                logger.warning(f"Notification {self.uuid} has no group")
            else:
                existing_notification_count = Notification.objects.filter(created_by_group=group).count()
                usage_limits = Subscription.compute_usage_limits(group)
                max_notification_count = usage_limits.max_notifications

                if (max_notification_count is not None) and (existing_notification_count >= max_notification_count):
                    diff = existing_notification_count - max_notification_count + 1
                    for notification in Notification.objects.filter(created_by_group=group) \
                            .order_by('attempted_at')[:diff].iterator():
                        id = notification.uuid
                        logger.info(f"Deleting Notification {id} because {group=} has reached the limit of {max_notification_count}")
                        try:
                            notification.delete()
                            logger.info(f"Deleted Notification {id} successfully")
                        except Exception:
                            logger.warning(f"Failed to delete Notification {id}", exc_info=True)
        else:
            logger.info('Updating an existing Notification')

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        event_id = str(self.event.uuid) if self.event else '[REMOVED]'
        np_id = str(self.notification_profile.uuid) if self.notification_profile else '[REMOVED]'
        ndm_id = str(self.notification_delivery_method.uuid) if self.notification_delivery_method else '[REMOVED]'
        return f"Event {event_id} / NP {np_id} / NDM {ndm_id} / {self.uuid}"
