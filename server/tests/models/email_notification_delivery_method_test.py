from typing import cast

import time
import pytest

from random import randint

from django.utils.html import escape

from moto import mock_aws

from processes.common.request_helpers import context_with_request
from processes.exception import NotificationRateLimitExceededException
from processes.models import (
   Event, NotificationDeliveryMethod, RunEnvironment, TaskExecution, TaskExecutionStatusChangeEvent,
   WorkflowExecution, WorkflowExecutionStatusChangeEvent,
)
from processes.serializers import (
    TaskExecutionSerializer, WorkflowExecutionSerializer
)

@pytest.mark.django_db
@mock_aws
def test_send_task_execution_event(run_environment: RunEnvironment,
        task_factory, task_execution_factory,
        email_notification_delivery_method_factory, mailoutbox):
    edm = email_notification_delivery_method_factory(
        run_environment=run_environment,
        email_to_addresses=['to@example.com'])

    task = task_factory(run_environment=run_environment)
    te = task_execution_factory(task=task, status=TaskExecution.Status.FAILED.value)
    event = TaskExecutionStatusChangeEvent(task_execution=te)

    context = context_with_request()
    ser_pe = dict(TaskExecutionSerializer(te, context=context).data)

    edm.send(event=event)

    assert len(mailoutbox) == 1
    m = mailoutbox[0]
    assert m.from_email == 'webmaster@cloudreactor.io'
    assert list(m.to) == ['to@example.com']
    assert m.subject == f"ERROR - Task Execution {te.uuid} of '{task.name}' finished with status {ser_pe['status']}"
    assert te.dashboard_url in m.body
    assert escape(task.name) in m.body
    assert escape(task.dashboard_url) in m.body
    assert escape(ser_pe['status']) in m.body
    assert escape(run_environment.name) in m.body
    assert escape(run_environment.dashboard_url) in m.body


@pytest.mark.django_db
@mock_aws
def test_send_workflow_execution_event(run_environment: RunEnvironment,
        workflow_factory, workflow_execution_factory,
        email_notification_delivery_method_factory, mailoutbox):
    edm = email_notification_delivery_method_factory(
        run_environment=run_environment,
        email_to_addresses=['to@example.com'])

    workflow = workflow_factory()
    we = workflow_execution_factory(workflow=workflow,
            status=WorkflowExecution.Status.TERMINATED_AFTER_TIME_OUT.value)
    event = WorkflowExecutionStatusChangeEvent(workflow_execution=we)

    context = context_with_request()
    ser_we = dict(WorkflowExecutionSerializer(we, context=context).data)

    edm.send(event=event)

    assert len(mailoutbox) == 1
    m = mailoutbox[0]
    assert m.from_email == 'webmaster@cloudreactor.io'
    assert list(m.to) == ['to@example.com']
    assert m.subject == f"CloudReactor Workflow '{workflow.name}' finished with status {ser_we['status']}"
    assert we.dashboard_url in m.body
    assert escape(workflow.name) in m.body
    assert escape(workflow.dashboard_url) in m.body
    assert escape(ser_we['status']) in m.body

TEST_RATE_LIMIT_PERIODS_SECONDS = 5

@pytest.mark.django_db
@pytest.mark.parametrize("""
    rate_limit_severity, send_count, event_severity, pause_seconds, num_allowed
""", [
    (None, 4, Event.SEVERITY_WARNING, 0, 2),
    (Event.SEVERITY_ERROR, 4, Event.SEVERITY_ERROR, 0, 2),
    (Event.SEVERITY_WARNING, 4, Event.SEVERITY_ERROR, 0, 4),
    (Event.SEVERITY_ERROR, 4, Event.SEVERITY_WARNING, 0, 2),
    (None, 4, Event.SEVERITY_ERROR, TEST_RATE_LIMIT_PERIODS_SECONDS + 1, 2),
    (None, 4, Event.SEVERITY_ERROR, 1, 2),
])
def test_rate_limiting(rate_limit_severity: int | None,
        send_count: int, event_severity: int | None, pause_seconds: int,
        num_allowed: int,
        basic_event_factory, email_notification_delivery_method_factory):
    edm = email_notification_delivery_method_factory()

    tier_index = randint(0, NotificationDeliveryMethod.MAX_RATE_LIMIT_TIERS - 1)

    setattr(edm, f'max_requests_per_period_{tier_index}', 2)
    setattr(edm, f'request_period_seconds_{tier_index}', TEST_RATE_LIMIT_PERIODS_SECONDS)
    setattr(edm, f'max_severity_{tier_index}', rate_limit_severity)

    #edm.save()

    event = basic_event_factory(severity=event_severity)

    call_count = {'n': 0}
    def counting_send(event_arg):
        assert event_arg.uuid == event.uuid
        call_count['n'] += 1
        return { 'success': True, 'call_count': call_count['n'] }

    setattr(edm, 'send', counting_send)

    for i in range(send_count):
        if i < num_allowed:
            assert not edm.will_be_rate_limited(event)

            expected_call_count = i + 1
            request_count = expected_call_count

            if rate_limit_severity is not None and event_severity > rate_limit_severity:
                request_count = None

            assert edm.send_if_not_rate_limited(event=event)['call_count'] == expected_call_count
            assert getattr(edm, f'request_count_in_period_{tier_index}') == request_count
        else:
            assert edm.will_be_rate_limited(event)
            assert getattr(edm, f'request_count_in_period_{tier_index}') == num_allowed

            with pytest.raises(Exception) as excinfo:
                # Ensure .send is not called when rate limited
                edm.send_if_not_rate_limited(event=event)

                assert call_count['n'] == num_allowed

            ex = excinfo.value
            assert isinstance(ex, NotificationRateLimitExceededException)
            nrlee = cast(NotificationRateLimitExceededException, ex)
            assert nrlee.event.uuid == event.uuid
            assert nrlee.rate_limit_tier_index == tier_index
            assert nrlee.delivery_method.uuid == edm.uuid


    if pause_seconds > 0:
        time.sleep(pause_seconds)

        if pause_seconds >= 5:
            assert not edm.will_be_rate_limited(event)
            assert edm.send_if_not_rate_limited(event=event)['call_count'] is not None
            assert getattr(edm, f'request_count_in_period_{tier_index}') == 1
        else:
            assert edm.will_be_rate_limited(event)

            with pytest.raises(Exception) as excinfo:
                # Ensure .send is not called when rate limited
                edm.send_if_not_rate_limited(event=event)

                assert call_count['n'] == num_allowed + 1

            ex = excinfo.value
            assert isinstance(ex, NotificationRateLimitExceededException)
            nrlee = cast(NotificationRateLimitExceededException, ex)
            assert nrlee.event.uuid == event.uuid
            assert nrlee.rate_limit_tier_index == tier_index
            assert nrlee.delivery_method.uuid == edm.uuid
