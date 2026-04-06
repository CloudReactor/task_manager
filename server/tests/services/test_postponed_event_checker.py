"""
Tests for PostponedEventChecker.check_all() and PostponedEventChecker.check_event().
"""
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

import pytest

from processes.models import (
    BasicEvent,
    Execution,
    RunEnvironment,
    Task,
    TaskExecution,
    TaskExecutionStatusChangeEvent,
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
def test_check_event_with_task_but_no_execution_triggers_and_routes_to_executable(
    task_execution_status_change_event_factory,
    task_factory,
):
    """When the event has a task (executable) but no task_execution, check_event()
    triggers the event and routes notifications to the task rather than an
    execution.  Returns True."""
    task = task_factory()
    event = task_execution_status_change_event_factory(
        task_execution=None,
        task=task,
        status=Execution.Status.FAILED,
        postponed_until=timezone.now() - timedelta(seconds=60),
        triggered_at=None,
    )

    checker = PostponedEventChecker()
    with patch.object(Task, 'send_event_notifications', return_value=0) as mock_notify:
        result = checker.check_event(event)

    assert result is True
    event.refresh_from_db()
    assert event.triggered_at is not None
    mock_notify.assert_called_once_with(event)


@pytest.mark.django_db
def test_check_event_returns_false_when_task_disabled(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """check_event() returns False, sets resolved_at, and leaves triggered_at
    unset when the executable (task) is disabled."""
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
    assert event.resolved_at is not None


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


@pytest.mark.django_db
def test_check_event_routes_to_run_environment_when_no_execution_or_executable(
    basic_event_factory,
):
    """When the event has no execution or executable but has a run_environment,
    check_event() triggers the event and routes notifications to the
    run_environment.  Returns True."""
    event = basic_event_factory(
        postponed_until=timezone.now() - timedelta(seconds=60),
        triggered_at=None,
    )

    checker = PostponedEventChecker()
    with patch.object(
        RunEnvironment, 'send_event_notifications', create=True, return_value=0
    ) as mock_notify:
        result = checker.check_event(event)

    assert result is True
    event.refresh_from_db()
    assert event.triggered_at is not None
    mock_notify.assert_called_once_with(event)


@pytest.mark.django_db
def test_check_event_returns_true_and_sets_triggered_at_when_no_target(
    basic_event_factory,
):
    """When the event has no execution, executable, or run_environment,
    check_event() still sets triggered_at and returns True (emits only a log
    warning; no send_event_notifications call is made)."""
    event = basic_event_factory(
        run_environment=None,
        postponed_until=timezone.now() - timedelta(seconds=60),
        triggered_at=None,
    )

    checker = PostponedEventChecker()
    result = checker.check_event(event)

    assert result is True
    event.refresh_from_db()
    assert event.triggered_at is not None


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


@pytest.mark.django_db
def test_check_all_skips_event_with_resolved_event(
    task_execution_status_change_event_factory,
    task_execution_factory,
    basic_event_factory,
):
    """Events whose resolved_event FK is non-null are excluded from the queryset."""
    resolving = basic_event_factory()
    te = task_execution_factory(status=Execution.Status.FAILED)
    utc_now = timezone.now()
    task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(seconds=60),
        triggered_at=None,
        resolved_event=resolving,
        resolved_at=None,
    )

    checker = PostponedEventChecker()
    assert checker.check_all() == 0


@pytest.mark.django_db
def test_check_all_triggers_event_at_upper_boundary(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """An event whose postponed_until is just below now (a few seconds ago) is
    included — verifies the lte upper end of the filter window."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=timezone.now() - timedelta(seconds=2),
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )

    checker = PostponedEventChecker()
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        assert checker.check_all() == 1


@pytest.mark.django_db
def test_check_all_triggers_event_at_lower_boundary(
    task_execution_status_change_event_factory,
    task_execution_factory,
):
    """An event whose postponed_until is just inside the MAX_POSTPONED_AGE_SECONDS
    window is included — verifies the gte lower end of the filter window."""
    te = task_execution_factory(status=Execution.Status.FAILED)
    # 10 s inside the boundary keeps the test deterministic even on slow CI
    postponed_until = timezone.now() - timedelta(
        seconds=PostponedEventChecker.MAX_POSTPONED_AGE_SECONDS - 10
    )
    task_execution_status_change_event_factory(
        task_execution=te,
        task=te.task,
        status=Execution.Status.FAILED,
        postponed_until=postponed_until,
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )

    checker = PostponedEventChecker()
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        assert checker.check_all() == 1


@pytest.mark.django_db
def test_check_all_mixed_batch(
    task_execution_status_change_event_factory,
    task_execution_factory,
    basic_event_factory,
):
    """check_all() returns 1 when the DB contains one valid event alongside
    events excluded by each individual filter predicate."""
    utc_now = timezone.now()

    # Valid — should be triggered
    te_valid = task_execution_factory(status=Execution.Status.FAILED)
    valid_event = task_execution_status_change_event_factory(
        task_execution=te_valid,
        task=te_valid.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(seconds=60),
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )

    # Excluded: postponed_until in the future
    te_future = task_execution_factory(status=Execution.Status.FAILED)
    task_execution_status_change_event_factory(
        task_execution=te_future,
        task=te_future.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now + timedelta(seconds=300),
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )

    # Excluded: too old
    te_old = task_execution_factory(status=Execution.Status.FAILED)
    task_execution_status_change_event_factory(
        task_execution=te_old,
        task=te_old.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(
            seconds=PostponedEventChecker.MAX_POSTPONED_AGE_SECONDS + 60
        ),
        triggered_at=None,
        resolved_event=None,
        resolved_at=None,
    )

    # Excluded: triggered_at already set
    te_triggered = task_execution_factory(status=Execution.Status.FAILED)
    task_execution_status_change_event_factory(
        task_execution=te_triggered,
        task=te_triggered.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(seconds=60),
        triggered_at=utc_now - timedelta(seconds=30),
        resolved_event=None,
        resolved_at=None,
    )

    # Excluded: resolved_event set
    resolving = basic_event_factory()
    te_resolved = task_execution_factory(status=Execution.Status.FAILED)
    task_execution_status_change_event_factory(
        task_execution=te_resolved,
        task=te_resolved.task,
        status=Execution.Status.FAILED,
        postponed_until=utc_now - timedelta(seconds=60),
        triggered_at=None,
        resolved_event=resolving,
        resolved_at=None,
    )

    checker = PostponedEventChecker()
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        count = checker.check_all()

    assert count == 1
    valid_event.refresh_from_db()
    assert valid_event.triggered_at is not None
