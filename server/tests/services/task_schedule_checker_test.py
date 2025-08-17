from typing import Optional

from datetime import datetime, timedelta
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


@pytest.mark.django_db
@pytest.mark.parametrize("""
    schedule_type, enabled, managed_probability, event_severity,
    schedule_updated_minutes_ago,
    last_execution_minutes_ago, should_expect_event
""", [
    (SCHEDULE_TYPE_CRON, True,  1.0, Event.SEVERITY_ERROR, 2 * 24 * 60, 60,   True),
    (SCHEDULE_TYPE_CRON, True,  1.0, Event.SEVERITY_ERROR, 2 * 24 * 60, 16,   False),
    (SCHEDULE_TYPE_CRON, False, 1.0, Event.SEVERITY_ERROR, 2 * 24 * 60, 60,   False),
    (SCHEDULE_TYPE_CRON, True,  0.9, Event.SEVERITY_ERROR, 2 * 24 * 60, 60,   False),
    (SCHEDULE_TYPE_CRON, True,  1.0, None,                 2 * 24 * 60, 60,   False),
    (SCHEDULE_TYPE_CRON, True,  1.0, Event.SEVERITY_ERROR,          10, 60,   False),
    (SCHEDULE_TYPE_CRON, True,  1.0, Event.SEVERITY_ERROR, 2 * 24 * 60, None, True),
    (SCHEDULE_TYPE_RATE, True,  1.0, Event.SEVERITY_ERROR, 2 * 24 * 60, 10,   False),
    (SCHEDULE_TYPE_RATE, True,  1.0, Event.SEVERITY_ERROR, 2 * 24 * 60, 42,   True),
    (SCHEDULE_TYPE_RATE, True,  1.0, Event.SEVERITY_ERROR, 2 * 24 * 60, None, True),
    (SCHEDULE_TYPE_RATE, False, 1.0, Event.SEVERITY_ERROR, 2 * 24 * 60, 42,   False),
    (SCHEDULE_TYPE_RATE, True,  0.5, Event.SEVERITY_ERROR, 2 * 24 * 60, 42,   False),
    (SCHEDULE_TYPE_RATE, True,  1.0, Event.SEVERITY_ERROR,          20, 42,   False),
    (None,               True,  1.0, Event.SEVERITY_ERROR, 2 * 24 * 60, None, False)
])
@mock_aws
def test_task_schedule_checker_missing_scheduled_executions(
        schedule_type: str, enabled: bool, managed_probability: float,
        event_severity: int,
        schedule_updated_minutes_ago: int,
        last_execution_minutes_ago: Optional[int],
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


    # TODO: modify scheduled_instance_count,
    task = task_factory(enabled=enabled, schedule=schedule, scheduled_instance_count=1,
            is_scheduling_managed=False, managed_probability=managed_probability,
            notification_event_severity_on_missing_execution=event_severity,
            schedule_updated_at = utc_now - timedelta(minutes=schedule_updated_minutes_ago))

    if last_execution_at is not None:
        task_execution_factory(task=task, started_at=last_execution_at)

    checker = TaskScheduleChecker()
    detection_at = timezone.now()
    checker.check_all()

    events = MissingScheduledTaskExecutionEvent.objects.filter(task=task)
    event: Event | None = None

    if should_expect_event:
        assert events.count() == 1
        event = events.first()

        assert event.uuid is not None
        assert event.created_by_group == task.created_by_group
        detection_timediff_seconds = (event.detected_at - detection_at).total_seconds()
        assert detection_timediff_seconds >= 0
        assert detection_timediff_seconds < 60
        assert event.severity == task.notification_event_severity_on_missing_execution
        assert event.grouping_key == f"missing_scheduled_task-{task.uuid}-{event.expected_execution_at.timestamp() // 60}"
        assert event.error_summary == f"Task '{task.name}' did not execute as scheduled at {event.expected_execution_at}"
        assert event.resolved_at is None
        assert event.resolved_event is None

        assert event.task == task
        assert event.task_execution is None
        assert event.schedule == task.schedule
        assert event.expected_execution_at is not None
        assert event.expected_execution_at == event.event_at
        assert event.expected_execution_at.second == 0
        assert event.expected_execution_at.microsecond == 0

        if schedule_type == SCHEDULE_TYPE_CRON:
            assert event.expected_execution_at.minute == schedule_minute
            assert event.expected_execution_at.hour == schedule_hour
        else:
            assert abs((event.expected_execution_at - utc_now).total_seconds()) < 60
    else:
        assert events.count() == 0

    # rechecking should not create new events
    checker.check_all()
    events = MissingScheduledTaskExecutionEvent.objects.filter(task=task)

    if should_expect_event:
        assert events.count() == 1
        assert events.first().uuid == event.uuid
    else:
        assert events.count() == 0


    utc_now = timezone.now()

    # simulate task execution starting to resolve the event
    task_execution = task_execution_factory(task=task, started_at=utc_now)

    events = MissingScheduledTaskExecutionEvent.objects.filter(task=task)

    if should_expect_event:
        assert events.count() == 2

        for new_event in events:
            assert new_event.task == task
            assert new_event.created_by_group == task.created_by_group
            assert new_event.grouping_key == event.grouping_key

            if new_event.uuid == event.uuid:
                timediff_seconds = (new_event.resolved_at - utc_now).total_seconds()
                assert new_event.task_execution is None
            else:
                timediff_seconds = (new_event.detected_at - utc_now).total_seconds()

                assert new_event.resolved_at is None
                assert new_event.resolved_event == event
                assert new_event.task_execution == task_execution

            assert timediff_seconds >= 0
            assert timediff_seconds < 60
    else:
        assert events.count() == 0
