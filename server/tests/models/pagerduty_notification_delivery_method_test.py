from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from processes.models import (
   Event, RunEnvironment, TaskExecutionStatusChangeEvent,
   WorkflowExecution, WorkflowExecutionStatusChangeEvent, Execution,
)


@pytest.mark.django_db
def test_send_task_execution_event(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        pager_duty_notification_delivery_method_factory):
    pdm = pager_duty_notification_delivery_method_factory(
        run_environment=run_environment,
        pagerduty_api_key='test_api_key_12345')

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task, status=Execution.Status.FAILED.value)
    event = TaskExecutionStatusChangeEvent(task_execution=te)
    event.error_summary = 'Test error summary'
    event.grouping_key = 'test-grouping-key'
    event.source = 'test-source'
    event.severity = Event.Severity.ERROR

    # Mock pdpyras.EventsAPISession
    with patch('processes.models.pagerduty_notification_delivery_method.pdpyras.EventsAPISession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.trigger.return_value = 'test-dedup-key-123'
        mock_session_class.return_value = mock_session

        result = pdm.send(event=event)

        # Verify the session was created with the correct API key
        mock_session_class.assert_called_once_with('test_api_key_12345', debug=False)

        # Verify trigger was called with the correct parameters
        mock_session.trigger.assert_called_once()
        call_args = mock_session.trigger.call_args

        # Check positional args and keyword args
        assert call_args.kwargs['summary'] == 'Test error summary'
        assert call_args.kwargs['source'] == 'test-source'
        assert call_args.kwargs['severity'] == 'error'
        assert call_args.kwargs['dedup_key'] == 'test-grouping-key'

        # Check that payload contains the expected fields with the templates
        payload = call_args.kwargs['payload']
        assert 'class' in payload
        assert 'component' in payload
        assert 'group' in payload

        # Verify result
        assert result['dedup_key'] == 'test-dedup-key-123'


@pytest.mark.django_db
def test_send_workflow_execution_event(run_environment: RunEnvironment,
        workflow_factory, workflow_execution_factory,
        pager_duty_notification_delivery_method_factory):
    pdm = pager_duty_notification_delivery_method_factory(
        run_environment=run_environment,
        pagerduty_api_key='test_api_key_67890')

    workflow = workflow_factory()
    we = workflow_execution_factory(workflow=workflow,
            status=Execution.Status.TERMINATED_AFTER_TIME_OUT.value)
    event = WorkflowExecutionStatusChangeEvent(workflow_execution=we)
    event.error_summary = 'Workflow timeout error'
    event.grouping_key = 'workflow-grouping-key'
    event.source = 'workflow-source'
    event.severity = Event.Severity.WARNING

    # Mock pdpyras.EventsAPISession
    with patch('processes.models.pagerduty_notification_delivery_method.pdpyras.EventsAPISession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.trigger.return_value = 'workflow-dedup-key-456'
        mock_session_class.return_value = mock_session

        result = pdm.send(event=event)

        # Verify the session was created with the correct API key
        mock_session_class.assert_called_once_with('test_api_key_67890', debug=False)

        # Verify trigger was called with the correct parameters
        mock_session.trigger.assert_called_once()
        call_args = mock_session.trigger.call_args

        assert call_args.kwargs['summary'] == 'Workflow timeout error'
        assert call_args.kwargs['source'] == 'workflow-source'
        assert call_args.kwargs['severity'] == 'warning'
        assert call_args.kwargs['dedup_key'] == 'workflow-grouping-key'

        # Verify result
        assert result['dedup_key'] == 'workflow-dedup-key-456'


@pytest.mark.django_db
def test_send_resolution_event(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        pager_duty_notification_delivery_method_factory):
    pdm = pager_duty_notification_delivery_method_factory(
        run_environment=run_environment,
        pagerduty_api_key='test_api_key_resolve')

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task, status=Execution.Status.SUCCEEDED.value)

    # Create a resolved event by setting resolved_event (is_resolution is read-only property)
    from processes.models import BasicEvent
    resolved_event = BasicEvent()
    event = TaskExecutionStatusChangeEvent(task_execution=te, resolved_event=resolved_event)
    event.grouping_key = 'resolve-grouping-key'

    # Mock pdpyras.EventsAPISession
    with patch('processes.models.pagerduty_notification_delivery_method.pdpyras.EventsAPISession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.resolve.return_value = 'resolved-successfully'
        mock_session_class.return_value = mock_session

        result = pdm.send(event=event)

        # Verify the session was created with the correct API key
        mock_session_class.assert_called_once_with('test_api_key_resolve', debug=False)

        # Verify resolve was called, not trigger
        mock_session.resolve.assert_called_once_with(dedup_key='resolve-grouping-key')
        mock_session.trigger.assert_not_called()

        # Verify result
        assert result['resolve_return_value'] == 'resolved-successfully'


@pytest.mark.django_db
def test_pagerduty_severity_mapping():
    from processes.models import PagerDutyNotificationDeliveryMethod

    # Test CRITICAL -> critical
    assert PagerDutyNotificationDeliveryMethod.pagerduty_severity_from_event_severity(
        Event.Severity.CRITICAL) == 'critical'

    # Test ERROR -> error
    assert PagerDutyNotificationDeliveryMethod.pagerduty_severity_from_event_severity(
        Event.Severity.ERROR) == 'error'

    # Test WARNING -> warning
    assert PagerDutyNotificationDeliveryMethod.pagerduty_severity_from_event_severity(
        Event.Severity.WARNING) == 'warning'

    # Test INFO -> info
    assert PagerDutyNotificationDeliveryMethod.pagerduty_severity_from_event_severity(
        Event.Severity.INFO) == 'info'

    # Test DEBUG -> info
    assert PagerDutyNotificationDeliveryMethod.pagerduty_severity_from_event_severity(
        Event.Severity.DEBUG) == 'info'

    # Test TRACE -> info
    assert PagerDutyNotificationDeliveryMethod.pagerduty_severity_from_event_severity(
        Event.Severity.TRACE) == 'info'
