import json
import logging
import textwrap

from django.db import models
from django.utils import timezone

from .alert_send_status import AlertSendStatus
from .named_with_uuid_and_run_environment_model import NamedWithUuidAndRunEnvironmentModel
from .event import Event
from .notification import Notification
from .notification_delivery_method import NotificationDeliveryMethod

logger = logging.getLogger(__name__)


class NotificationProfile(NamedWithUuidAndRunEnvironmentModel):
    """
    A NotificationProfile specifies one or more configured methods of notifying
    users or external sources of events that trigger when one or more
    conditions are satisfied.
    """

    class Meta:
        unique_together = (('name', 'created_by_group'),)

    enabled = models.BooleanField(default=True)

    notification_delivery_methods = models.ManyToManyField(NotificationDeliveryMethod, blank=True)

    def send(self, event: Event) -> None:
        if not self.enabled:
            logger.info(f"Skipping Notification Profile {self.uuid} / {self.name} because it is disabled")
            return

        for ndm in self.notification_delivery_methods.all():
            notification = Notification(event=event, notification_profile=self,
                                        notification_delivery_method=ndm,
                                        send_status=AlertSendStatus.SENDING)
            notification.save()

            # TODO: Queue this, implement retry
            try:
                send_result = ndm.send(event)

                send_result_json = json.dumps(send_result)

                if len(send_result_json) > Notification.MAX_SEND_RESULT_LENGTH:
                    logger.warning(f"send result too long for notification {notification.uuid}: {send_result_json[0:Notification.MAX_SEND_RESULT_LENGTH]}")
                    # TODO: add some of the json
                    send_result = { 'success': True, 'warning': 'send result too long' }

                notification.send_result = send_result
                notification.send_status = AlertSendStatus.SUCCEEDED
                notification.completed_at = timezone.now()
            except Exception as e:
                logger.exception(f"Exception occurred sending notification using delivery method #{ndm.uuid}")
                notification.send_status = AlertSendStatus.FAILED

                message = textwrap.shorten(str(e), width=Notification.MAX_SEND_RESULT_LENGTH)

                notification.send_result = {
                    'exception': {
                        'type': type(e).__name__,
                        'message': message
                    }
                }

            notification.save()

        logger.info(f"Finished sending notifications for event #{event.uuid}")
