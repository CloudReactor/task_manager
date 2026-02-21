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


@pytest.mark.django_db
@mock_aws
def test_post_save_creates_status_change_event_on_failure(task_execution_factory):
    """Saving a TaskExecution with FAILED status should create a TaskExecutionStatusChangeEvent."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.status = Execution.Status.FAILED
        te.save()

    assert TaskExecutionStatusChangeEvent.objects.filter(
        task_execution=te,
        status=Execution.Status.FAILED
    ).count() == 1


@pytest.mark.django_db
@mock_aws
def test_post_save_creates_status_change_event_on_timeout(task_execution_factory):
    """Saving a TaskExecution with TERMINATED_AFTER_TIME_OUT status should create a status change event."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.status = Execution.Status.TERMINATED_AFTER_TIME_OUT
        te.save()

    assert TaskExecutionStatusChangeEvent.objects.filter(
        task_execution=te,
        status=Execution.Status.TERMINATED_AFTER_TIME_OUT
    ).count() == 1


@pytest.mark.django_db
@mock_aws
def test_post_save_creates_status_change_event_on_success_when_severity_configured(
        task_execution_factory):
    """Saving a TaskExecution with SUCCEEDED status creates a status change event when the task has a success severity configured."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.task.notification_event_severity_on_success = Event.Severity.INFO
        te.task.save()
        te.status = Execution.Status.SUCCEEDED
        te.save()

    assert TaskExecutionStatusChangeEvent.objects.filter(
        task_execution=te,
        status=Execution.Status.SUCCEEDED
    ).count() == 1


@pytest.mark.django_db
@mock_aws
def test_post_save_no_status_change_event_on_success_without_severity(
        task_execution_factory):
    """Saving a TaskExecution with SUCCEEDED status does not create a status change event when notification_event_severity_on_success is None (the default)."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.status = Execution.Status.SUCCEEDED
        te.save()

    assert TaskExecutionStatusChangeEvent.objects.filter(
        task_execution=te,
        status=Execution.Status.SUCCEEDED
    ).count() == 0


@pytest.mark.django_db
@mock_aws
def test_post_save_no_status_change_event_when_skip_event_generation(
        task_execution_factory):
    """No status change event should be created when skip_event_generation is True."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.skip_event_generation = True
        te.status = Execution.Status.FAILED
        te.save()

    assert TaskExecutionStatusChangeEvent.objects.filter(
        task_execution=te
    ).count() == 0


@pytest.mark.django_db
@mock_aws
def test_post_save_no_status_change_event_when_task_disabled(task_execution_factory):
    """No status change event should be created when the task is disabled."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.task.enabled = False
        te.task.save()
        te.status = Execution.Status.FAILED
        te.save()

    assert TaskExecutionStatusChangeEvent.objects.filter(
        task_execution=te
    ).count() == 0


@pytest.mark.django_db
@mock_aws
def test_post_save_no_duplicate_status_change_events(task_execution_factory):
    """Saving a TaskExecution multiple times with the same completed status should not create duplicate events."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.status = Execution.Status.FAILED
        te.save()
        te.save()  # Second save with same status

    assert TaskExecutionStatusChangeEvent.objects.filter(
        task_execution=te,
        status=Execution.Status.FAILED
    ).count() == 1


@pytest.mark.django_db
@mock_aws
def test_post_save_no_status_change_event_on_aborted_when_service_updated_after_start(
        task_execution_factory):
    """No status change event should be created when a TaskExecution is ABORTED and aws_ecs_service_updated_at is after started_at."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te = task_execution_factory()
        te.task.aws_ecs_service_updated_at = timezone.now()
        te.task.save()
        te.status = Execution.Status.ABORTED
        te.save()

    assert TaskExecutionStatusChangeEvent.objects.filter(
        task_execution=te
    ).count() == 0


@pytest.mark.django_db
@mock_aws
def test_post_save_failure_event_postponed_when_configured(task_execution_factory):
    """When failure postponement is configured, the status change event should have postponed_until set and triggered_at unset, and no notification should be sent."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0) as mock_notify:
        te = task_execution_factory()
        te.task.postponed_failure_before_success_seconds = 3600
        te.task.max_postponed_failure_count = 3
        te.task.save()
        te.status = Execution.Status.FAILED
        te.save()

    event = TaskExecutionStatusChangeEvent.objects.get(task_execution=te)
    assert event.postponed_until is not None
    assert event.triggered_at is None
    mock_notify.assert_not_called()


@pytest.mark.django_db
@mock_aws
def test_post_save_failure_event_not_postponed_without_configuration(task_execution_factory):
    """Without postponement configuration, the status change event should be triggered immediately (triggered_at set, notification sent)."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0) as mock_notify:
        te = task_execution_factory()
        te.status = Execution.Status.FAILED
        te.save()

    event = TaskExecutionStatusChangeEvent.objects.get(task_execution=te)
    assert event.postponed_until is None
    assert event.triggered_at is not None
    mock_notify.assert_called_once()


@pytest.mark.django_db
@mock_aws
def test_post_save_postponed_failure_event_accelerated_on_max_repeated_failures(
        task_execution_factory):
    """When the same task fails again while a postponed event exists and the failure count reaches max_postponed_failure_count, the event should be triggered."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0) as mock_notify:
        te1 = task_execution_factory()
        te1.task.postponed_failure_before_success_seconds = 3600
        te1.task.max_postponed_failure_count = 1
        te1.task.save()
        te1.status = Execution.Status.FAILED
        te1.save()

        # First failure creates a postponed event; no notification sent yet
        assert mock_notify.call_count == 0
        event = TaskExecutionStatusChangeEvent.objects.get(task=te1.task)
        assert event.postponed_until is not None
        assert event.triggered_at is None

        # Second failure of the same task: count reaches max, event is accelerated
        te2 = task_execution_factory(task=te1.task)
        te2.status = Execution.Status.FAILED
        te2.save()

    event.refresh_from_db()
    assert event.triggered_at is not None
    assert mock_notify.call_count == 1


@pytest.mark.django_db
@mock_aws
def test_post_save_postponed_failure_event_resolved_after_sufficient_successes(
        task_execution_factory):
    """When a task succeeds enough times to meet required_success_count_to_clear_failure, the postponed event should be resolved."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0):
        te1 = task_execution_factory()
        te1.task.postponed_failure_before_success_seconds = 3600
        te1.task.max_postponed_failure_count = 3
        te1.task.required_success_count_to_clear_failure = 1
        te1.task.save()
        te1.status = Execution.Status.FAILED
        te1.save()

        event = TaskExecutionStatusChangeEvent.objects.get(task=te1.task)
        assert event.postponed_until is not None
        assert event.resolved_at is None

        # Task succeeds: count_with_success_status reaches required threshold → resolved
        te2 = task_execution_factory(task=te1.task)
        te2.status = Execution.Status.SUCCEEDED
        te2.save()

    event.refresh_from_db()
    assert event.resolved_at is not None
    assert event.triggered_at is None


@pytest.mark.django_db
@mock_aws
def test_post_save_timeout_event_postponed_when_configured(task_execution_factory):
    """When timeout postponement is configured, a TERMINATED_AFTER_TIME_OUT event should be postponed."""
    with patch.object(TaskExecution, 'send_event_notifications', return_value=0) as mock_notify:
        te = task_execution_factory()
        te.task.postponed_timeout_before_success_seconds = 3600
        te.task.max_postponed_timeout_count = 3
        te.task.save()
        te.status = Execution.Status.TERMINATED_AFTER_TIME_OUT
        te.save()

    event = TaskExecutionStatusChangeEvent.objects.get(task_execution=te)
    assert event.postponed_until is not None
    assert event.triggered_at is None
    mock_notify.assert_not_called()
