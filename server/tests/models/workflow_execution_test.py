from unittest.mock import patch

from moto import mock_aws
import pytest

from processes.models import (
    Event,
    Execution,
    WorkflowExecution,
    WorkflowExecutionStatusChangeEvent,
)


@pytest.mark.django_db
@mock_aws
def test_post_save_creates_status_change_event_on_failure(workflow_execution_factory):
    """Saving a WorkflowExecution with FAILED status should create a WorkflowExecutionStatusChangeEvent."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0):
        we = workflow_execution_factory()
        we.status = Execution.Status.FAILED
        we.save()

    assert WorkflowExecutionStatusChangeEvent.objects.filter(
        workflow_execution=we,
        status=Execution.Status.FAILED
    ).count() == 1


@pytest.mark.django_db
@mock_aws
def test_post_save_creates_status_change_event_on_timeout(workflow_execution_factory):
    """Saving a WorkflowExecution with TERMINATED_AFTER_TIME_OUT status should create a status change event."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0):
        we = workflow_execution_factory()
        we.status = Execution.Status.TERMINATED_AFTER_TIME_OUT
        we.save()

    assert WorkflowExecutionStatusChangeEvent.objects.filter(
        workflow_execution=we,
        status=Execution.Status.TERMINATED_AFTER_TIME_OUT
    ).count() == 1


@pytest.mark.django_db
@mock_aws
def test_post_save_creates_status_change_event_on_success_when_severity_configured(
        workflow_execution_factory):
    """Saving a WorkflowExecution with SUCCEEDED status creates a status change event when the workflow has a success severity configured."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0):
        we = workflow_execution_factory()
        we.workflow.notification_event_severity_on_success = Event.Severity.INFO
        we.workflow.save()
        we.status = Execution.Status.SUCCEEDED
        we.save()

    assert WorkflowExecutionStatusChangeEvent.objects.filter(
        workflow_execution=we,
        status=Execution.Status.SUCCEEDED
    ).count() == 1


@pytest.mark.django_db
@mock_aws
def test_post_save_no_status_change_event_on_success_without_severity(
        workflow_execution_factory):
    """Saving a WorkflowExecution with SUCCEEDED status does not create a status change event when notification_event_severity_on_success is None (the default)."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0):
        we = workflow_execution_factory()
        we.status = Execution.Status.SUCCEEDED
        we.save()

    assert WorkflowExecutionStatusChangeEvent.objects.filter(
        workflow_execution=we,
        status=Execution.Status.SUCCEEDED
    ).count() == 0


@pytest.mark.django_db
@mock_aws
def test_post_save_no_status_change_event_when_skip_event_generation(
        workflow_execution_factory):
    """No status change event should be created when skip_event_generation is True."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0):
        we = workflow_execution_factory()
        we.skip_event_generation = True
        we.status = Execution.Status.FAILED
        we.save()

    assert WorkflowExecutionStatusChangeEvent.objects.filter(
        workflow_execution=we
    ).count() == 0


@pytest.mark.django_db
@mock_aws
def test_post_save_no_status_change_event_when_workflow_disabled(workflow_execution_factory):
    """No status change event should be created when the workflow is disabled."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0):
        we = workflow_execution_factory()
        we.workflow.enabled = False
        we.workflow.save()
        we.status = Execution.Status.FAILED
        we.save()

    assert WorkflowExecutionStatusChangeEvent.objects.filter(
        workflow_execution=we
    ).count() == 0


@pytest.mark.django_db
@mock_aws
def test_post_save_no_duplicate_status_change_events(workflow_execution_factory):
    """Saving a WorkflowExecution multiple times with the same completed status should not create duplicate events."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0):
        we = workflow_execution_factory()
        we.status = Execution.Status.FAILED
        we.save()
        we.save()  # Second save with same status

    assert WorkflowExecutionStatusChangeEvent.objects.filter(
        workflow_execution=we,
        status=Execution.Status.FAILED
    ).count() == 1


@pytest.mark.django_db
@mock_aws
def test_post_save_no_status_change_event_while_in_progress(workflow_execution_factory):
    """No status change event should be created while the workflow execution is still in progress (RUNNING)."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0):
        we = workflow_execution_factory(status=Execution.Status.RUNNING)
        we.save()

    assert WorkflowExecutionStatusChangeEvent.objects.filter(
        workflow_execution=we
    ).count() == 0


@pytest.mark.django_db
@mock_aws
def test_post_save_failure_event_postponed_when_configured(workflow_execution_factory):
    """When failure postponement is configured, the status change event should have postponed_until set and triggered_at unset, and no notification should be sent."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0) as mock_notify:
        we = workflow_execution_factory()
        we.workflow.postponed_failure_before_success_seconds = 3600
        we.workflow.max_postponed_failure_count = 3
        we.workflow.save()
        we.status = Execution.Status.FAILED
        we.save()

    event = WorkflowExecutionStatusChangeEvent.objects.get(workflow_execution=we)
    assert event.postponed_until is not None
    assert event.triggered_at is None
    mock_notify.assert_not_called()


@pytest.mark.django_db
@mock_aws
def test_post_save_failure_event_not_postponed_without_configuration(workflow_execution_factory):
    """Without postponement configuration, the status change event should be triggered immediately (triggered_at set, notification sent)."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0) as mock_notify:
        we = workflow_execution_factory()
        we.status = Execution.Status.FAILED
        we.save()

    event = WorkflowExecutionStatusChangeEvent.objects.get(workflow_execution=we)
    assert event.postponed_until is None
    assert event.triggered_at is not None
    mock_notify.assert_called_once()


@pytest.mark.django_db
@mock_aws
def test_post_save_timeout_event_postponed_when_configured(workflow_execution_factory):
    """When timeout postponement is configured, a TERMINATED_AFTER_TIME_OUT event should be postponed."""
    with patch.object(WorkflowExecution, 'send_event_notifications', return_value=0) as mock_notify:
        we = workflow_execution_factory()
        we.workflow.postponed_timeout_before_success_seconds = 3600
        we.workflow.max_postponed_timeout_count = 3
        we.workflow.save()
        we.status = Execution.Status.TERMINATED_AFTER_TIME_OUT
        we.save()

    event = WorkflowExecutionStatusChangeEvent.objects.get(workflow_execution=we)
    assert event.postponed_until is not None
    assert event.triggered_at is None
    mock_notify.assert_not_called()
