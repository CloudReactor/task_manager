import logging

from django.db import transaction
from django.utils import timezone

from ..models import ExecutionStatusChangeEvent, TaskExecutionStatusChangeEvent

logger = logging.getLogger(__name__)


class PostponedEventChecker:
    def check_all(self) -> int:
        utc_now = timezone.now()

        triggered_count = 0
        for event in TaskExecutionStatusChangeEvent.objects.filter(
                postponed_until__lte=utc_now, triggered_at__isnull=True,
                resolved_at__isnull=True):
            with transaction.atomic():
                try:
                    if self.check_event(event):
                        triggered_count += 1
                except Exception:
                    logger.exception(f"Exception checking event {event.uuid}")

        return triggered_count


    def check_event(self, event: ExecutionStatusChangeEvent) -> bool:
        execution = event.get_execution()

        if not execution:
            logger.info(f"For event {event.uuid}, Execution is not found")
            return False

        schedulable = execution.get_schedulable()

        if not schedulable:
            logger.info(f"For Execution {execution.uuid}, Schedulable is not found")
            return False

        if not schedulable.enabled:
            logger.info(f"Scheduable {schedulable.uuid} named '{schedulable.name}' is not enabled")
            return False

        logger.info(f"Found event {event.uuid} for schedulable '{schedulable.name}'")

        event.triggered_at = timezone.now()
        event.save()

        logger.info(f"Accelerated event {event.uuid} because postponed_until is in the past")

        execution.send_event_notifications(event)

        return True
