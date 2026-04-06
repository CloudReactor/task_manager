from __future__ import annotations

from typing import Final

from datetime import timedelta
import logging

from django.db import transaction
from django.utils import timezone

from ..models import Event

logger = logging.getLogger(__name__)


class PostponedEventChecker:
    MAX_POSTPONED_AGE_SECONDS: Final[int] = 7 * 24 * 60 * 60

    def check_all(self) -> int:
        logger.info("Checking for postponed events that should be triggered ...")

        utc_now = timezone.now()

        event_count = 0
        triggered_count = 0
        for event in Event.objects.filter(
                postponed_until__gte=utc_now - timedelta(seconds=self.MAX_POSTPONED_AGE_SECONDS),
                postponed_until__lte=utc_now,
                triggered_at__isnull=True, resolved_event__isnull=True,
                resolved_at__isnull=True).iterator():
            event_count += 1

            with transaction.atomic():
                try:
                    if self.check_event(event):
                        triggered_count += 1
                except Exception:
                    logger.exception(f"Exception checking event {event.uuid}")

        logger.info(f"Done checking for postponed events, triggered {triggered_count} out of {event_count} events")

        return triggered_count


    def check_event(self, event: Event) -> bool:
        executable = event.get_executable()

        if executable:
            if executable.enabled:
                logger.info(f"Found postponed event {event.uuid} for executable '{executable.name}'")
            else:
                logger.info(f"Executable {executable.uuid} named '{executable.name}' is not enabled")
                event.resolved_at = timezone.now()
                event.save()
                return False

        event.triggered_at = timezone.now()
        event.save()

        logger.info(f"Accelerated event {event.uuid} because postponed_until is in the past")

        execution = event.get_execution()

        if execution:
            execution.send_event_notifications(event)
        elif executable:
            executable.send_event_notifications(event)
        else:
            run_env = event.run_environment

            if run_env:
                logger.info(f"Event {event.uuid} has no execution or executable but has Run Environment {run_env.uuid}, sending notifications for the Run Environment ...")
                run_env.send_event_notifications(event)
            else:
                logger.warning(f"Event {event.uuid} has no execution, executable, or Run Environment, not sending notifications")

        return True
