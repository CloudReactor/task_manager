import pytest

from django.utils.html import escape

from django.contrib.auth.models import Group

from model_bakery import baker

from moto import mock_ecs, mock_sts, mock_events

from processes.common.request_helpers import context_with_request
from processes.models import (
    RunEnvironment
)
from processes.serializers import (
    TaskExecutionSerializer,
    WorkflowExecutionSerializer
)

@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_task_execution_send(group: Group, run_environment: RunEnvironment, mailoutbox):
    task = baker.make('Task',
            run_environment=run_environment,
            created_by_group=group)
    te = baker.make('TaskExecution',
            task=task
    )
    enp = baker.make('EmailNotificationProfile',
            to_addresses=['to@example.com'],
            created_by_group=group
    )

    context = context_with_request()
    ser_pe = dict(TaskExecutionSerializer(te, context=context).data)

    enp.send(task_execution=te)

    assert len(mailoutbox) == 1
    m = mailoutbox[0]
    assert m.from_email == 'webmaster@cloudreactor.io'
    assert list(m.to) == ['to@example.com']
    assert m.subject == f"CloudReactor Task '{task.name}' finished with status {ser_pe['status']}"
    assert te.dashboard_url in m.body
    assert escape(task.name) in m.body
    assert escape(task.dashboard_url) in m.body
    assert escape(ser_pe['status']) in m.body
    assert escape(run_environment.name) in m.body
    assert escape(run_environment.dashboard_url) in m.body

@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_workflow_execution_send(group: Group, mailoutbox):
    workflow = baker.make('Workflow', created_by_group=group)
    we = baker.make('WorkflowExecution',
            workflow=workflow
    )
    enp = baker.make('EmailNotificationProfile',
            to_addresses=['to@example.com'],
            created_by_group=group
    )

    context = context_with_request()
    ser_we = dict(WorkflowExecutionSerializer(we, context=context).data)

    enp.send(workflow_execution=we)

    assert len(mailoutbox) == 1
    m = mailoutbox[0]
    assert m.from_email == 'webmaster@cloudreactor.io'
    assert list(m.to) == ['to@example.com']
    assert m.subject == f"CloudReactor Workflow '{workflow.name}' finished with status {ser_we['status']}"
    assert we.dashboard_url in m.body
    assert escape(workflow.name) in m.body
    assert escape(workflow.dashboard_url) in m.body
    assert escape(ser_we['status']) in m.body
