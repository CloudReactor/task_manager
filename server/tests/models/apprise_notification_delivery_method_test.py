from typing import cast
from unittest.mock import MagicMock, patch

import pytest
import apprise

from django.conf import settings

from processes.models import (
   Event, RunEnvironment, TaskExecutionStatusChangeEvent,
   WorkflowExecutionStatusChangeEvent, Execution, AppriseNotificationDeliveryMethod
)


@pytest.mark.django_db
def test_send_task_execution_event(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        apprise_notification_delivery_method_factory):
    andm = apprise_notification_delivery_method_factory(
        run_environment=run_environment,
        apprise_url='slack://xoxb-test-token/C123456/U123456')

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task, status=Execution.Status.FAILED.value)
    event = TaskExecutionStatusChangeEvent(task_execution=te)
    event.error_summary = 'Task failed unexpectedly'
    event.error_details_message = 'Exit code 1'
    event.severity = Event.Severity.ERROR

    # Mock apprise.Apprise
    with patch('processes.models.apprise_notification_delivery_method.apprise.Apprise') as mock_apprise_class:
        mock_apprise = MagicMock()
        mock_apprise.add.return_value = True
        mock_apprise.notify.return_value = 1  # 1 service notified
        mock_apprise_class.return_value = mock_apprise

        result = andm.send(event=event)

        # Verify Apprise instance was created with asset
        mock_apprise_class.assert_called_once()
        call_args = mock_apprise_class.call_args
        asset = call_args.kwargs.get('asset')
        assert asset is not None
        assert 'cloudreactor' in asset.app_id.lower()

        # Verify URL was added
        mock_apprise.add.assert_called_once_with('slack://xoxb-test-token/C123456/U123456')

        # Verify notify was called with correct parameters
        mock_apprise.notify.assert_called_once()
        notify_call = mock_apprise.notify.call_args
        assert notify_call.kwargs['body'] is not None
        assert notify_call.kwargs['title'] is not None
        assert notify_call.kwargs['notify_type'] == apprise.NotifyType.FAILURE  # ERROR severity maps to failure
        assert 'Task failed unexpectedly' in notify_call.kwargs['title']

        # Verify result
        assert result['success'] == 1


@pytest.mark.django_db
def test_send_workflow_execution_event(run_environment: RunEnvironment,
        workflow_factory, workflow_execution_factory,
        apprise_notification_delivery_method_factory):
    andm = apprise_notification_delivery_method_factory(
        run_environment=run_environment,
        apprise_url='mailto://user:pass@gmail.com')

    workflow = workflow_factory()
    we = workflow_execution_factory(workflow=workflow,
            status=Execution.Status.TERMINATED_AFTER_TIME_OUT.value)
    event = WorkflowExecutionStatusChangeEvent(workflow_execution=we)
    event.error_summary = 'Workflow timeout'
    event.error_details_message = 'Workflow did not complete within time limit'
    event.severity = Event.Severity.WARNING

    with patch('processes.models.apprise_notification_delivery_method.apprise.Apprise') as mock_apprise_class:
        mock_apprise = MagicMock()
        mock_apprise.add.return_value = True
        mock_apprise.notify.return_value = 1
        mock_apprise_class.return_value = mock_apprise

        result = andm.send(event=event)

        # Verify notify was called
        mock_apprise.notify.assert_called_once()
        notify_call = mock_apprise.notify.call_args
        assert notify_call.kwargs['notify_type'] == apprise.NotifyType.WARNING  # WARNING severity maps to warning
        assert 'Workflow timeout' in notify_call.kwargs['title']

        assert result['success'] == 1


@pytest.mark.django_db
def test_send_with_critical_severity(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        apprise_notification_delivery_method_factory):
    andm = apprise_notification_delivery_method_factory(
        run_environment=run_environment,
        apprise_url='discord://webhook-url')

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task)
    event = TaskExecutionStatusChangeEvent(task_execution=te)
    event.severity = Event.Severity.CRITICAL

    with patch('processes.models.apprise_notification_delivery_method.apprise.Apprise') as mock_apprise_class:
        mock_apprise = MagicMock()
        mock_apprise.add.return_value = True
        mock_apprise.notify.return_value = 1
        mock_apprise_class.return_value = mock_apprise

        result = andm.send(event=event)

        notify_call = mock_apprise.notify.call_args
        assert notify_call.kwargs['notify_type'] == apprise.NotifyType.FAILURE  # CRITICAL maps to failure


@pytest.mark.django_db
def test_send_with_info_severity(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        apprise_notification_delivery_method_factory):
    andm = apprise_notification_delivery_method_factory(
        run_environment=run_environment,
        apprise_url='teams://webhook-url')

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task)
    event = TaskExecutionStatusChangeEvent(task_execution=te)
    event.severity = Event.Severity.INFO

    with patch('processes.models.apprise_notification_delivery_method.apprise.Apprise') as mock_apprise_class:
        mock_apprise = MagicMock()
        mock_apprise.add.return_value = True
        mock_apprise.notify.return_value = 1
        mock_apprise_class.return_value = mock_apprise

        result = andm.send(event=event)

        notify_call = mock_apprise.notify.call_args
        assert notify_call.kwargs['notify_type'] == apprise.NotifyType.INFO


@pytest.mark.django_db
def test_send_raises_on_missing_url(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        apprise_notification_delivery_method_factory):
    andm = apprise_notification_delivery_method_factory(
        run_environment=run_environment,
        apprise_url=None)

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task)
    event = TaskExecutionStatusChangeEvent(task_execution=te)

    with pytest.raises(ValueError, match="Apprise URL is required"):
        andm.send(event=event)


@pytest.mark.django_db
def test_send_raises_on_invalid_url(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        apprise_notification_delivery_method_factory):
    andm = apprise_notification_delivery_method_factory(
        run_environment=run_environment,
        apprise_url='invalid://malformed-url')

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task)
    event = TaskExecutionStatusChangeEvent(task_execution=te)

    with patch('processes.models.apprise_notification_delivery_method.apprise.Apprise') as mock_apprise_class:
        mock_apprise = MagicMock()
        mock_apprise.add.return_value = False  # Invalid URL
        mock_apprise_class.return_value = mock_apprise

        with pytest.raises(ValueError, match="Invalid Apprise URL"):
            andm.send(event=event)


@pytest.mark.django_db
def test_send_handles_notification_error(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        apprise_notification_delivery_method_factory):
    andm = apprise_notification_delivery_method_factory(
        run_environment=run_environment,
        apprise_url='slack://invalid-token')

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task)
    event = TaskExecutionStatusChangeEvent(task_execution=te)

    with patch('processes.models.apprise_notification_delivery_method.apprise.Apprise') as mock_apprise_class:
        mock_apprise = MagicMock()
        mock_apprise.add.return_value = True
        mock_apprise.notify.side_effect = Exception("Connection refused")
        mock_apprise_class.return_value = mock_apprise

        with pytest.raises(Exception, match="Connection refused"):
            andm.send(event=event)


@pytest.mark.django_db
def test_send_multiple_services_notified(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        apprise_notification_delivery_method_factory):
    """Test that success count reflects multiple services notified."""
    andm = apprise_notification_delivery_method_factory(
        run_environment=run_environment,
        apprise_url='slack://token1 discord://token2')

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task)
    event = TaskExecutionStatusChangeEvent(task_execution=te)

    with patch('processes.models.apprise_notification_delivery_method.apprise.Apprise') as mock_apprise_class:
        mock_apprise = MagicMock()
        mock_apprise.add.return_value = True
        mock_apprise.notify.return_value = 2  # 2 services notified
        mock_apprise_class.return_value = mock_apprise

        result = andm.send(event=event)

        assert result['success'] == 2
