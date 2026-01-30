import json
import logging
import textwrap

from django.db import models
from django.utils import timezone

from ..exception.notification_rate_limit_exceeded_exception import \
    NotificationRateLimitExceededException

from .notification_send_status import NotificationSendStatus
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
            initial_send_status = NotificationSendStatus.SENDING if ndm.enabled else NotificationSendStatus.SKIPPED

            notification = Notification(event=event, notification_profile=self,
                    notification_delivery_method=ndm,
                    send_status=initial_send_status)
            notification.save()

            if not ndm.enabled:
                logger.info(f"Skipping Notification Delivery Method {ndm.uuid} / {ndm.name} because it is disabled")
                continue

            # TODO: Queue this, implement retry
            try:
                send_result = ndm.send_if_not_rate_limited(event)

                send_result_json = json.dumps(send_result)

                if len(send_result_json) > Notification.MAX_SEND_RESULT_LENGTH:
                    logger.warning(f"send result too long for notification {notification.uuid}: {send_result_json[0:Notification.MAX_SEND_RESULT_LENGTH]}")
                    # TODO: add some of the json
                    send_result = { 'success': True, 'warning': 'send result too long' }

                notification.send_result = send_result
                notification.send_status = NotificationSendStatus.SUCCEEDED
                notification.completed_at = timezone.now()
            except NotificationRateLimitExceededException as nrkee:
                logger.info(f"Notification rate limit exceeded for delivery method {ndm.uuid} for event {event.uuid}")
                notification.send_status = NotificationSendStatus.RATE_LIMITED

                tier_index = nrkee.rate_limit_tier_index
                notification.rate_limit_max_requests_per_period = getattr(ndm,
                        f'max_requests_per_period_{tier_index}')
                notification.rate_limit_request_period_seconds = getattr(ndm,
                        f'request_period_seconds_{tier_index}')
                notification.rate_limit_max_severity = getattr(ndm, f'max_severity_{tier_index}')
                notification.rate_limit_tier_index = tier_index
            except Exception as e:
                logger.exception(f"Exception occurred sending notification using delivery method {ndm.uuid}")
                notification.send_status = NotificationSendStatus.FAILED

                notification.exception_type = type(e).__name__
                notification.exception_message = textwrap.shorten(str(e),
                        width=Notification.MAX_EXCEPTION_MESSAGE_LENGTH)

            notification.save()

        logger.info(f"Finished sending notifications for event #{event.uuid}")
