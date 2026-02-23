from datetime import datetime, timedelta, timezone as dt_timezone
import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

import intervals as I

from ..common.notification import *
from ..models import *

LOOKBACK_DURATION_SECONDS = 5 * 60
DEFAULT_MAX_STARTUP_DURATION_SECONDS = 5 * 60

logger = logging.getLogger(__name__)


class ServiceConcurrencyChecker:
    TRIGGERED_EVENT_SUMMARY_TEMPLATE = \
        """Service '{{task.name}}' had an insufficient instance count of {{detected_concurrency}} between {{interval_start_at}} and {{interval_end_at}}, required instance count of {{required_concurrency}}"""

    RESOLVED_EVENT_SUMMARY_TEMPLATE = \
        """Service '{{task.name}}' now has a sufficient instance count of at least {{required_concurrency}}"""

    def check_all(self):
        for service in Task.objects.filter(enabled=True, min_service_instance_count__gt=0,
                notification_event_severity_on_insufficient_instances__isnull=False):
            with transaction.atomic():
                try:
                    self.check_service(service)
                except Exception:
                    logger.exception(f"Exception checking service {service.uuid}")

    def check_service(self, service: Task):
        logger.info(f"Found service {service.uuid} named '{service.name}'")

        utc_now = timezone.now()
        utc_timestamp = utc_now.timestamp()
        start_dt = utc_now - timedelta(seconds=LOOKBACK_DURATION_SECONDS)

        # We shouldn't look at Task Executions until a delay after the Task was created
        max_delay_seconds = service.max_manual_start_delay_before_alert_seconds \
                or DEFAULT_MAX_STARTUP_DURATION_SECONDS
        first_expected_execution_at = service.created_at + timedelta(
                seconds=max_delay_seconds)

        # Also if we recently updated the service, don't look until after the service was setup
        # TODO: use a more generic field for other infrastructures
        if service.aws_ecs_service_updated_at:
            first_expected_execution_at = service.aws_ecs_service_updated_at + timedelta(
                seconds=max_delay_seconds)

        if first_expected_execution_at > start_dt:
            start_dt = first_expected_execution_at

        interval_start_timestamp = start_dt.timestamp()

        if interval_start_timestamp >= utc_timestamp:
            logger.info(f"First expected start time {start_dt} is after current time, skipping service {service.uuid}")
            return

        qs = TaskExecution.objects.filter(
            Q(task=service) &
            (
              Q(finished_at__gte=start_dt) |
              Q(finished_at__isnull=True)
            ) &
            (
              Q(marked_done_at__gte=start_dt) |
              Q(marked_done_at__isnull=True)
            ) &
            (
              Q(kill_started_at__gte=start_dt) |
              Q(kill_started_at__isnull=True)
            )
        )

        interval_dict = I.IntervalDict()
        interval_dict[I.closed(interval_start_timestamp, utc_timestamp)] = 0
        combiner = lambda x, y: x + y

        for te in qs:
            start_timestamp = min(max(te.started_at.timestamp(), interval_start_timestamp), utc_timestamp)
            end_timestamp = utc_timestamp
            is_end_closed = True

            done_at = te.finished_at or te.marked_done_at or te.kill_started_at or te.kill_finished_at
            if done_at:
                end_timestamp = min(done_at.timestamp(), end_timestamp)
                is_end_closed = False

            te_interval_dict = I.IntervalDict()
            if is_end_closed:
                te_interval = I.closed(start_timestamp, end_timestamp)
            else:
                te_interval = I.closedopen(start_timestamp, end_timestamp)

            te_interval_dict[te_interval] = 1
            interval_dict = interval_dict.combine(te_interval_dict, how=combiner)

        min_concurrency_found = None
        min_concurrency_found_interval = None
        for kv in interval_dict.items():
            interval = kv[0]
            concurrency = kv[1]

            if min_concurrency_found is None or concurrency <= min_concurrency_found:
                min_concurrency_found = concurrency
                min_concurrency_found_interval = interval

        if (min_concurrency_found is None) or (min_concurrency_found_interval is None):
            logger.error(f'Unexpected state: {min_concurrency_found=}, {min_concurrency_found_interval=}')
        elif (service.min_service_instance_count is not None) and (min_concurrency_found < service.min_service_instance_count):
            logger.info(f"Found insufficient min concurrency {min_concurrency_found} for service {service.uuid}")

            event = InsufficientServiceTaskExecutionsEvent.objects.filter(
                    task=service).order_by('-detected_at', '-event_at').first()

            if (event is None) or event.resolved_at:
                logger.info(f"Found insufficient min concurrency {min_concurrency_found}, creating event")

                # set microseconds to 0 so that formatted date in alert doesn't have fractional seconds
                current_event = InsufficientServiceTaskExecutionsEvent(
                    severity=service.notification_event_severity_on_insufficient_instances,
                    created_by_group=service.created_by_group,
                    run_environment=service.run_environment,
                    task=service,
                    interval_start_at=datetime.fromtimestamp(min_concurrency_found_interval.lower, tz=dt_timezone.utc).replace(microsecond=0),
                    interval_end_at=datetime.fromtimestamp(min_concurrency_found_interval.upper, tz=dt_timezone.utc).replace(microsecond=0),
                    detected_concurrency=min_concurrency_found,
                    required_concurrency=service.min_service_instance_count,
                    resolved_at=None
                )
                current_event.save()

                service.send_event_notifications(current_event)
            else:
                logger.info(f"There already exists a InsufficientServiceTaskExecutionsEvent detected at {event.detected_at}, not creating again")
                # TODO: create event if the last event was old

        else:
            logger.info(f"Found sufficient min concurrency {min_concurrency_found} for service {service.uuid}")

            for event in InsufficientServiceTaskExecutionsEvent.objects.filter(task=service,
                    resolved_at__isnull=True):
                logger.info(f"Resolving InsufficientServiceTaskExecutionsEvent {event.uuid} since concurrency is sufficient")
                event.resolved_at = utc_now
                event.save()

                resolving_event = InsufficientServiceTaskExecutionsEvent(
                    severity=service.notification_event_severity_on_sufficient_instances_restored,
                    created_by_group=service.created_by_group,
                    run_environment=service.run_environment,
                    task=service,
                    interval_start_at=event.interval_start_at,
                    interval_end_at=event.interval_end_at,
                    detected_concurrency=min_concurrency_found,
                    required_concurrency=event.required_concurrency,
                    resolved_event=event,
                    resolved_at=utc_now
                )
                resolving_event.save()

                service.send_event_notifications(resolving_event)
