from typing import List

from datetime import timedelta
import random

from django.utils import timezone

import pytest

from moto import mock_ecs, mock_sts, mock_events

from processes.models import (
    Subscription,
    SubscriptionPlan,
    WorkflowExecution
)

@pytest.mark.django_db
@pytest.mark.parametrize("""
  max_executions, reservation_count, max_to_purge
""", [
  (100, 0, -1),
  (100, 1, -1),
  (100, 1, 50),
  (4, 0, -1),
  (4, 1, 2),
  (2, 0, -1),
  (2, 1, -1),
  (0, 0, -1)
])
@mock_ecs
@mock_sts
@mock_events
def test_purge_history(max_executions: int, reservation_count: int,
        max_to_purge: int, subscription_plan: SubscriptionPlan,
        workflow_factory, workflow_execution_factory):
    workflow = workflow_factory()

    utc_now = timezone.now()

    subscription = Subscription(group=workflow.created_by_group,
          subscription_plan=subscription_plan, active=True,
          start_at=utc_now - timedelta(minutes=1))
    subscription.save()

    num_completed = 3
    num_in_progress = 5

    another_workflow = workflow_factory(created_by_group=workflow.created_by_group)
    another_workflow_execution = workflow_execution_factory(workflow=another_workflow,
            status=WorkflowExecution.Status.SUCCEEDED)

    completed_workflow_execution_ids: List[int] = []

    for i in range(num_completed):
        we = workflow_execution_factory(workflow=workflow,
                status=random.choice(WorkflowExecution.COMPLETED_STATUSES),
                finished_at=utc_now-timedelta(minutes=i))
        we.save()
        completed_workflow_execution_ids.append(we.id)

    in_progress_workflow_execution_ids: List[int] = []

    for i in range(num_in_progress):
        we = workflow_execution_factory(workflow=workflow,
                status=random.choice(WorkflowExecution.IN_PROGRESS_STATUSES))
        # We need to set after saving due to auto_add_now
        we.started_at = utc_now - timedelta(minutes=i)
        we.save()
        in_progress_workflow_execution_ids.append(we.id)

    plan = subscription.subscription_plan
    assert plan is not None
    plan.max_workflow_execution_history_items = max_executions
    plan.save()

    allowed_executions = max_executions - reservation_count

    num_purged = workflow.purge_history(reservation_count,
            max_to_purge=max_to_purge)

    expected_to_purge = max(num_completed + num_in_progress - allowed_executions, 0)

    if max_to_purge > 0:
        expected_to_purge = min(expected_to_purge, max_to_purge)

    assert num_purged == expected_to_purge

    if max_to_purge < 0:
        assert workflow.workflowexecution_set.count() <= allowed_executions

    num_completed_to_keep = max(num_completed - num_purged, 0)

    for i in range(num_completed):
        id = completed_workflow_execution_ids[i]
        exists = (WorkflowExecution.objects.filter(id=id).count() == 1)
        if i < num_completed_to_keep:
            assert exists
        else:
            assert not exists

    num_in_progress_to_keep = max(num_in_progress -
            (num_purged - (num_completed - num_completed_to_keep)),  0)

    for i in range(num_in_progress):
        id = in_progress_workflow_execution_ids[i]
        exists = WorkflowExecution.objects.filter(id=id).count() == 1

        if i < num_in_progress_to_keep:
            assert exists
        else:
            assert not exists

    assert WorkflowExecution.objects.filter(id=another_workflow_execution.id).count() == 1