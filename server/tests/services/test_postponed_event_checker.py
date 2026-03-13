"""
Tests for PostponedEventChecker.check_all() and PostponedEventChecker.check_event().
"""
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

import pytest

from processes.models import (
    TaskExecution,
    TaskExecutionStatusChangeEvent,
    Execution,
)
from processes.services.postponed_event_checker import PostponedEventChecker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_triggerable_event(
    task_execution_status_change_event_factory,
    task_execution_factory,
    *,
    seconds_ago: int = 60,
    task_execution: TaskExecution | None = None,
) -> TaskExecutionStatusChangeEvent:
    """Create a TaskExecutionStatusChangeEvent whose postponed_until is in the
    recent past so check_all() will pick it up."""
    te = task_execution or task_execution_factory(status=Execution.Status.FAILED)
    utc_now = timezone.now()
    return task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(seconds=seconds_ago),
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )


# ---------------------------------------------------------------------------
# check_event() — unit-level tests (no DB queryset, pass event directly)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_check_event_returns_false_when_no_task_execution(
    task_execution_status_change_event_factory,
    task_factory,
):
    """check_event() returns False when the event has no associated task execution."""
    event = task_execution_status_change_event_factory(
        task_execution=None,
        task=task_factory(),
        status=Execution.Status.FAILED,
        postponed_until=timezone.now() - timedelta(seconds=60),
        triggered_at=None,
    )

    checker = PostponedEventChecker()
    result = checker.check_event(event)

    assert result is False
    event.refresh_from_db()
    assert event.triggered_at is None


@pytest.mark.django_db
def test_check_event_returns_false_when_task_disabled(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """check_event() returns False when the task is disabled."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    te.task.enabled = False
    te.task.save()

    event = task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=timezone.now() - timedelta(seconds=60),
        triggered_at=None,
    )

    checker = PostponedEventChecker()
    result = checker.check_event(event)

    assert result is False
    event.refresh_from_db()
    assert event.triggered_at is None


@pytest.mark.django_db
def test_check_event_sets_triggered_at_and_sends_notifications(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """check_event() sets triggered_at, saves the event, calls send_event_notifications,
    and returns True for a valid, enabled execution."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    event = task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=timezone.now() - timedelta(seconds=60),
        triggered_at=None,
    )

    checker = PostponedEventChecker()
    with patch.object(TaskExecution, 'send_event_notifications', return_value=1) as mock_notify:
        result = checker.check_event(event)

    assert result is True
    event.refresh_from_db()
    assert event.triggered_at is not None
    mock_notify.assert_called_once_with(event)


@pytest.mark.django_db
def test_check_event_sends_the_triggerable_event_object(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """Notifications are sent with the correct event instance."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    event = task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=timezone.now() - timedelta(seconds=60),
        triggered_at=None,
    )

    checker = PostponedEventChecker()
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0) as mock_notify:
        checker.check_event(event)

    assert mock_notify.call_args.args[0].uuid == event.uuid


# ---------------------------------------------------------------------------
# check_all() — integration tests using DB queryset
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_check_all_returns_zero_when_no_events():
    """check_all() returns 0 when there are no events in the DB."""
    checker = PostponedEventChecker()
    assert checker.check_all() == 0


@pytest.mark.django_db
def test_check_all_returns_zero_when_postponed_until_is_in_future(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """Events whose postponed_until is still in the future are not triggered."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=timezone.now() + timedelta(seconds=300),
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )

    checker = PostponedEventChecker()
    assert checker.check_all() == 0


@pytest.mark.django_db
def test_check_all_returns_zero_when_postponed_until_is_too_old(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """Events older than MAX_POSTPONED_AGE_SECONDS are not triggered."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    too_old = timezone.now() - timedelta(
        seconds=PostponedEventChecker.MAX_POSTPONED_AGE_SECONDS + 60
    )
    task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=too_old,
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )

    checker = PostponedEventChecker()
    assert checker.check_all() == 0


@pytest.mark.django_db
def test_check_all_skips_already_triggered_events(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """Events that already have triggered_at set are skipped."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    utc_now = timezone.now()
    task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(seconds=60),
        triggered_at=utc_now - timedelta(seconds=30),
        resolved_event=None,
        resolved_at=None,
    )

    checker = PostponedEventChecker()
    assert checker.check_all() == 0


@pytest.mark.django_db
def test_check_all_skips_already_resolved_at_events(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """Events that already have resolved_at set are skipped."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    utc_now = timezone.now()
    task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(seconds=60),
        triggered_at=None,
        resolved_event=None,
        resolved_at=utc_now - timedelta(seconds=10),
    )

    checker = PostponedEventChecker()
    assert checker.check_all() == 0


@pytest.mark.django_db
def test_check_all_triggers_valid_event_and_returns_one(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """check_all() triggers a single valid event and returns 1."""
    event = _make_triggerable_event(
        task_execution_status_change_event_factory,
        task_execution_factory,
    )

    checker = PostponedEventChecker()
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        count = checker.check_all()

    assert count == 1
    event.refresh_from_db()
    assert event.triggered_at is not None


@pytest.mark.django_db
def test_check_all_triggers_multiple_valid_events(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """check_all() triggers all qualifying events and returns the correct count."""
    for _ in range(3):
        _make_triggerable_event(
            task_execution_status_change_event_factory,
            task_execution_factory,
        )

    checker = PostponedEventChecker()
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        count = checker.check_all()

    assert count == 3


@pytest.mark.django_db
def test_check_all_skips_event_for_disabled_task(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """check_all() skips events whose task is disabled and returns 0."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    te.task.enabled = False
    te.task.save()

    _make_triggerable_event(
        task_execution_status_change_event_factory,
        task_execution_factory,
        task_execution=te,
    )

    checker = PostponedEventChecker()
    assert checker.check_all() == 0


@pytest.mark.django_db
def test_check_all_continues_after_exception(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """check_all() logs the exception and continues processing remaining events."""
    te_good = task_execution_factory(status=Execution.Status.FAILED)
    te_bad = task_execution_factory(status=Execution.Status.FAILED)

    utc_now = timezone.now()
    bad_event = task_execution_status_change_event_factory(
        task_execution=te_bad,
        task=te_bad.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(seconds=120),
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )
    good_event = task_execution_status_change_event_factory(
        task_execution=te_good,
        task=te_good.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(seconds=60),
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )

    call_count = 0

    def raise_once(event: TaskExecutionStatusChangeEvent) -> bool:
        nonlocal call_count
        call_count += 1
        if event.uuid == bad_event.uuid:
            raise RuntimeError("Simulated failure")
        # Mimic real triggered_at assignment so the good event is properly processed
        event.triggered_at = timezone.now()
        event.save()
        return True

    checker = PostponedEventChecker()
    with patch.object(checker, 'check_event', side_effect=raise_once):
        count = checker.check_all()

    assert count == 1
    assert call_count == 2
    good_event.refresh_from_db()
    assert good_event.triggered_at is not None
    bad_event.refresh_from_db()
    assert bad_event.triggered_at is None


@pytest.mark.django_db
def test_check_all_does_not_trigger_same_event_twice(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """Calling check_all() twice does not double-trigger the same event."""
    _make_triggerable_event(
        task_execution_status_change_event_factory,
        task_execution_factory,
    )

    checker = PostponedEventChecker()
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        first = checker.check_all()
        second = checker.check_all()

    assert first == 1
    assert second == 0
