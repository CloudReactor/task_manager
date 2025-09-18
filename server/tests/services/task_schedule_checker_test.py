from typing import Optional

from datetime import datetime, timedelta
import logging
from django.utils import timezone

from processes.models import (
    Event,
    TaskExecution,
    MissingScheduledTaskExecutionEvent
)

from processes.services.task_schedule_checker import TaskScheduleChecker

import pytest

from moto import mock_aws


SCHEDULE_TYPE_CRON = 'C'
SCHEDULE_TYPE_RATE = 'R'

logger = logging.getLogger(__name__)


@pytest.mark.django_db
@pytest.mark.parametrize("""
    schedule_type, enabled, instance_count, managed_probability, event_severity,
    schedule_updated_minutes_ago,
    last_execution_minutes_ago, should_expect_event, last_execution_counts
""", [
    (SCHEDULE_TYPE_CRON, True,  1, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, 60,   True,  False),
    (SCHEDULE_TYPE_CRON, True,  1, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, 16,   False, True),
    (SCHEDULE_TYPE_CRON, False, 1, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, 60,   False, False),
    (SCHEDULE_TYPE_CRON, True,  2, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, 10,   True,  True),
    (SCHEDULE_TYPE_CRON, True,  3, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, 10,   True, True),
    (SCHEDULE_TYPE_CRON, True,  1, 0.9,   Event.SEVERITY_ERROR, 2 * 24 * 60, 60,   False, True),
    (SCHEDULE_TYPE_CRON, True,  1, 1.0,                   None, 2 * 24 * 60, 60,   False, True),
    (SCHEDULE_TYPE_CRON, False, 1, 1.0, Event.SEVERITY_WARNING, 2 * 24 * 60, 60,   False, True),
    (SCHEDULE_TYPE_CRON, True,  1, 1.0,   Event.SEVERITY_ERROR,          10, 60,   False, True),
    (SCHEDULE_TYPE_CRON, True,  1, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, None, True,  False),
    (SCHEDULE_TYPE_RATE, True,  1, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, 10,   False, True),
    (SCHEDULE_TYPE_RATE, True,  1, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, 42,   True,  False),
    (SCHEDULE_TYPE_RATE, True,  1, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, None, True,  False),
    (SCHEDULE_TYPE_RATE, False, 1, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, 42,   False, False),
    (SCHEDULE_TYPE_RATE, True,  2, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, 10,   True,  True),
    (SCHEDULE_TYPE_RATE, True,  1, 0.5,   Event.SEVERITY_ERROR, 2 * 24 * 60, 42,   False, True),
    (SCHEDULE_TYPE_RATE, True,  1, 1.0,   Event.SEVERITY_ERROR,          20, 42,   False, True),
    (None,               True,  1, 1.0,   Event.SEVERITY_ERROR, 2 * 24 * 60, None, False, False)
])
@mock_aws
def test_task_schedule_checker_missing_scheduled_executions(
        schedule_type: str, enabled: bool, instance_count: int,
        managed_probability: float, event_severity: int,
        schedule_updated_minutes_ago: int,
        last_execution_minutes_ago: Optional[int], last_execution_counts: bool,
        should_expect_event: bool, task_factory, task_execution_factory):
    utc_now = timezone.now()

    now_minute = utc_now.minute
    now_hour = utc_now.hour

    last_execution_at: Optional[datetime] = None

    if last_execution_minutes_ago is not None:
        last_execution_at = utc_now - timedelta(minutes=last_execution_minutes_ago)

    schedule = ''
    schedule_hour: int | None = None
    schedule_minute: int | None = None

    if schedule_type == SCHEDULE_TYPE_CRON:
        schedule_hour = now_hour
        schedule_minute = now_minute - 15

        while schedule_minute < 0:
            schedule_minute += 60
            schedule_hour -= 1

            if schedule_hour < 0:
                schedule_hour += 24

        schedule = f'cron({schedule_minute} {schedule_hour} * * ? *)'
    elif schedule_type == SCHEDULE_TYPE_RATE:
        schedule = 'rate(30 minutes)'


    task = task_factory(enabled=enabled, schedule=schedule,
            scheduled_instance_count=instance_count,
            is_scheduling_managed=False, managed_probability=managed_probability,
            notification_event_severity_on_missing_execution=event_severity,
            schedule_updated_at = utc_now - timedelta(minutes=schedule_updated_minutes_ago))

    if last_execution_at is not None:
        task_execution_factory(task=task, started_at=last_execution_at)

    event: Event | None = None
    previous_event: Event | None = None

    checker = TaskScheduleChecker()

    for _ in range(2):
        detection_at = timezone.now()
        checker.check_all()

        events = MissingScheduledTaskExecutionEvent.objects.filter(task=task)

        if should_expect_event:
            assert events.count() == 1
            event = events.first()

            if previous_event:
                assert event.uuid == previous_event.uuid
                assert event.detected_at == previous_event.detected_at
                assert event.missing_execution_count == previous_event.missing_execution_count
            else:
                detection_timediff_seconds = (event.detected_at - detection_at).total_seconds()
                assert detection_timediff_seconds >= 0
                assert detection_timediff_seconds < 60

            previous_event = event

            assert event.uuid is not None
            assert event.created_by_group == task.created_by_group
            assert event.severity == event_severity
            assert event.severity == task.notification_event_severity_on_missing_execution
            assert event.grouping_key == f"missing_scheduled_task-{task.uuid}-{event.expected_execution_at.timestamp() // 60}"
            assert event.error_summary == f"Task '{task.name}' did not execute as scheduled at {event.expected_execution_at}"
            assert event.resolved_at is None
            assert event.resolved_event is None

            assert event.task == task
            assert event.task_execution is None
            assert event.schedule == schedule
            assert event.schedule == task.schedule
            assert event.expected_execution_at is not None
            assert event.expected_execution_at == event.event_at
            assert event.expected_execution_at.second == 0
            assert event.expected_execution_at.microsecond == 0

            expected_missing_count = instance_count

            if last_execution_at and last_execution_counts:
                expected_missing_count -= 1

            assert event.missing_execution_count == expected_missing_count

            if schedule_type == SCHEDULE_TYPE_CRON:
                assert event.expected_execution_at.minute == schedule_minute
                assert event.expected_execution_at.hour == schedule_hour
            else:
                assert abs((event.expected_execution_at - utc_now).total_seconds()) < 60
        else:
            assert events.count() == 0


    utc_now = timezone.now()

    logger.info("Creating task execution to maybe resolve event")

    # simulate task execution starting to resolve the event
    task_execution = task_execution_factory(task=task, started_at=utc_now)

    logger.info(f"Created task execution {task_execution.uuid} started at {task_execution.started_at}")

    for i in range(2):
        logger.info(f"Checking events after task execution created, iteration {i}")

        events = MissingScheduledTaskExecutionEvent.objects.filter(task=task)

        if should_expect_event:
            if instance_count <= 2:
                assert events.count() == 2

                for new_event in events:
                    assert new_event.detected_at is not None
                    assert new_event.task == task
                    assert new_event.created_by_group == task.created_by_group
                    assert new_event.grouping_key == event.grouping_key
                    assert new_event.severity == event.severity

                    if new_event.uuid == event.uuid:
                        timediff_seconds = (new_event.resolved_at - utc_now).total_seconds()
                        assert new_event.task_execution is None

                        assert new_event.error_summary == event.error_summary
                    else:
                        timediff_seconds = (new_event.detected_at - utc_now).total_seconds()

                        assert new_event.detected_at >= event.detected_at
                        assert new_event.resolved_at is None
                        assert new_event.resolved_event == event
                        assert new_event.error_summary == f"Task '{task.name}' has started after being late according to its schedule"
                        assert new_event.task_execution == task_execution

                    assert timediff_seconds >= 0
                    assert timediff_seconds < 60
            else:
                # Event should not be resolved until all expected instances have started
                assert events.count() == 1
                new_event = events.first()
                assert new_event.uuid == event.uuid
                assert new_event.resolved_at is None
                assert new_event.task_execution is None

        else:
            assert events.count() == 0

        checker.check_all()