"""
Tests for Execution.maybe_create_and_send_status_change_event(),
exercised through TaskExecution DB instances.
"""
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from moto import mock_aws
import pytest

from processes.models import (
    Event,
    Execution,
    TaskExecution,
    TaskExecutionStatusChangeEvent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finish(te: TaskExecution, status: Execution.Status) -> None:
    """Set a terminal status and finished_at without triggering post_save logic."""
    te.status = status.value
    te.finished_at = timezone.now()


# ---------------------------------------------------------------------------
# skip_event_generation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_returns_none_when_skip_event_generation(task_execution_factory):
    te = task_execution_factory()
    te.skip_event_generation = True
    _finish(te, Execution.Status.FAILED)

    result = te.maybe_create_and_send_status_change_event()

    assert result is None
    assert TaskExecutionStatusChangeEvent.objects.filter(task_execution=te).count() == 0


# ---------------------------------------------------------------------------
# Schedulable guards
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_returns_none_when_task_disabled(task_execution_factory):
    te = task_execution_factory()
    te.task.enabled = False
    te.task.save()
    _finish(te, Execution.Status.FAILED)

    result = te.maybe_create_and_send_status_change_event()

    assert result is None
    assert TaskExecutionStatusChangeEvent.objects.filter(task_execution=te).count() == 0


# ---------------------------------------------------------------------------
# should_create_status_change_event — age guard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_returns_none_when_finished_at_too_old(task_execution_factory):
    te = task_execution_factory()
    te.status = Execution.Status.FAILED.value
    te.finished_at = timezone.now() - timedelta(
        seconds=Execution.MAX_STATUS_CHANGE_AGE_SECONDS + 1)

    result = te.maybe_create_and_send_status_change_event()

    assert result is None
    assert TaskExecutionStatusChangeEvent.objects.filter(task_execution=te).count() == 0


@pytest.mark.django_db
@mock_aws
def test_creates_event_when_finished_at_within_max_age(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.status = Execution.Status.FAILED.value
        te.finished_at = timezone.now() - timedelta(
            seconds=Execution.MAX_STATUS_CHANGE_AGE_SECONDS - 60)

        result = te.maybe_create_and_send_status_change_event()

    assert result is not None
    assert TaskExecutionStatusChangeEvent.objects.filter(task_execution=te).count() == 1


# ---------------------------------------------------------------------------
# Severity selection
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_returns_none_when_severity_none_for_succeeded(task_execution_factory):
    te = task_execution_factory()
    te.task.notification_event_severity_on_success = None
    te.task.save()
    _finish(te, Execution.Status.SUCCEEDED)

    result = te.maybe_create_and_send_status_change_event()

    assert result is None
    assert TaskExecutionStatusChangeEvent.objects.filter(task_execution=te).count() == 0


@pytest.mark.django_db
@mock_aws
def test_returns_none_when_severity_is_severity_none_for_succeeded(task_execution_factory):
    te = task_execution_factory()
    te.task.notification_event_severity_on_success = Event.Severity.NONE
    te.task.save()
    _finish(te, Execution.Status.SUCCEEDED)

    result = te.maybe_create_and_send_status_change_event()

    assert result is None
    assert TaskExecutionStatusChangeEvent.objects.filter(task_execution=te).count() == 0


@pytest.mark.django_db
@mock_aws
def test_returns_none_when_severity_none_for_failed(task_execution_factory):
    te = task_execution_factory()
    te.task.notification_event_severity_on_failure = None
    te.task.save()
    _finish(te, Execution.Status.FAILED)

    result = te.maybe_create_and_send_status_change_event()

    assert result is None
    assert TaskExecutionStatusChangeEvent.objects.filter(task_execution=te).count() == 0


@pytest.mark.django_db
@mock_aws
def test_returns_none_when_severity_none_for_timeout(task_execution_factory):
    te = task_execution_factory()
    te.task.notification_event_severity_on_timeout = None
    te.task.save()
    _finish(te, Execution.Status.TERMINATED_AFTER_TIME_OUT)

    result = te.maybe_create_and_send_status_change_event()

    assert result is None
    assert TaskExecutionStatusChangeEvent.objects.filter(task_execution=te).count() == 0


@pytest.mark.django_db
@mock_aws
def test_uses_error_severity_for_unhandled_status(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        _finish(te, Execution.Status.STOPPED)

        result = te.maybe_create_and_send_status_change_event()

    assert result is not None
    assert result.severity == Event.Severity.ERROR


@pytest.mark.django_db
@mock_aws
def test_uses_success_severity_for_succeeded(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.task.notification_event_severity_on_success = Event.Severity.INFO
        te.task.save()
        _finish(te, Execution.Status.SUCCEEDED)

        result = te.maybe_create_and_send_status_change_event()

    assert result is not None
    assert result.severity == Event.Severity.INFO


@pytest.mark.django_db
@mock_aws
def test_uses_failure_severity_for_failed(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.task.notification_event_severity_on_failure = Event.Severity.CRITICAL
        te.task.save()
        _finish(te, Execution.Status.FAILED)

        result = te.maybe_create_and_send_status_change_event()

    assert result is not None
    assert result.severity == Event.Severity.CRITICAL


@pytest.mark.django_db
@mock_aws
def test_uses_timeout_severity_for_timeout(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.task.notification_event_severity_on_timeout = Event.Severity.WARNING
        te.task.save()
        _finish(te, Execution.Status.TERMINATED_AFTER_TIME_OUT)

        result = te.maybe_create_and_send_status_change_event()

    assert result is not None
    assert result.severity == Event.Severity.WARNING


# ---------------------------------------------------------------------------
# Event is saved and returned
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_event_is_persisted(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        _finish(te, Execution.Status.FAILED)

        result = te.maybe_create_and_send_status_change_event()

    assert result is not None
    assert result.pk is not None
    assert TaskExecutionStatusChangeEvent.objects.filter(pk=result.pk).exists()


@pytest.mark.django_db
@mock_aws
def test_event_status_matches_execution_status(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        _finish(te, Execution.Status.FAILED)

        result = te.maybe_create_and_send_status_change_event()

    assert result is not None
    assert result.status == Execution.Status.FAILED


# ---------------------------------------------------------------------------
# No duplicate events
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_no_duplicate_events_on_second_call(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        _finish(te, Execution.Status.FAILED)

        te.maybe_create_and_send_status_change_event()
        result2 = te.maybe_create_and_send_status_change_event()

    assert result2 is None
    assert TaskExecutionStatusChangeEvent.objects.filter(task_execution=te).count() == 1


# ---------------------------------------------------------------------------
# Postponement
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_notifications_sent_when_not_postponed(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0) as mock_notify:
        te = task_execution_factory()
        _finish(te, Execution.Status.FAILED)

        result = te.maybe_create_and_send_status_change_event()

    assert result is not None
    mock_notify.assert_called_once_with(event=result)


@pytest.mark.django_db
@mock_aws
def test_notifications_not_sent_when_postponed(task_execution_factory):
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0) as mock_notify:
        te = task_execution_factory()
        te.task.postponed_failure_before_success_seconds = 3600
        te.task.max_postponed_failure_count = 3
        te.task.save()
        _finish(te, Execution.Status.FAILED)

        result = te.maybe_create_and_send_status_change_event()

    assert result is not None
    assert result.postponed_until is not None
    mock_notify.assert_not_called()
