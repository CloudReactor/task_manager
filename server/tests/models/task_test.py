from typing import List

from datetime import timedelta
import random

from django.utils import timezone

import pytest

from moto import mock_aws
from processes.models import (
    Subscription,
    SubscriptionPlan,
    TaskExecution
)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  max_executions, reservation_count, max_to_purge
""", [
  (100, 0, -1),
  (100, 1, -1),
  (4, 0, -1),
  (4, 1, 2),
  (4, 1, -1),
  (2, 0, -1),
  (2, 1, -1),
  (0, 0, -1)
])
@mock_aws
def test_purge_history(max_executions: int, reservation_count: int,
        max_to_purge: int, subscription_plan: SubscriptionPlan,
        task_factory, task_execution_factory):
    task = task_factory()

    utc_now = timezone.now()

    subscription = Subscription(group=task.created_by_group,
          subscription_plan=subscription_plan, active=True,
          start_at=utc_now - timedelta(minutes=1))
    subscription.save()

    num_completed = 3
    num_in_progress = 5

    another_task = task_factory(created_by_group=task.created_by_group)
    another_task_execution = task_execution_factory(task=another_task,
            status=TaskExecution.Status.SUCCEEDED)

    completed_task_execution_ids: List[int] = []

    for i in range(num_completed):
        te = task_execution_factory(task=task,
                status=random.choice(TaskExecution.COMPLETED_STATUSES),
                finished_at=utc_now-timedelta(minutes=i))
        te.save()
        completed_task_execution_ids.append(te.id)

    in_progress_task_execution_ids: List[int] = []

    for i in range(num_in_progress):
        te = task_execution_factory(task=task,
                status=random.choice(TaskExecution.IN_PROGRESS_STATUSES))
        # We need to set after saving due to auto_add_now
        te.started_at = utc_now - timedelta(minutes=i)
        te.save()
        in_progress_task_execution_ids.append(te.id)

    plan = subscription.subscription_plan
    assert plan is not None
    plan.max_task_execution_history_items = max_executions
    plan.save()

    allowed_executions = max_executions - reservation_count

    num_purged = task.purge_history(reservation_count=reservation_count,
            max_to_purge=max_to_purge)

    expected_to_purge = max(num_completed + num_in_progress - allowed_executions, 0)

    if max_to_purge > 0:
        expected_to_purge = min(expected_to_purge, max_to_purge)

    assert num_purged == expected_to_purge

    if max_to_purge < 0:
        assert task.taskexecution_set.count() <= allowed_executions

    num_completed_to_keep = max(num_completed - num_purged, 0)

    for i in range(num_completed):
        id = completed_task_execution_ids[i]
        exists = (TaskExecution.objects.filter(id=id).count() == 1)
        if i < num_completed_to_keep:
            assert exists
        else:
            assert not exists

    num_in_progress_to_keep = max(num_in_progress -
            (num_purged - (num_completed - num_completed_to_keep)),  0)

    for i in range(num_in_progress):
        id = in_progress_task_execution_ids[i]
        exists = TaskExecution.objects.filter(id=id).count() == 1

        if i < num_in_progress_to_keep:
            assert exists
        else:
            assert not exists

    assert TaskExecution.objects.filter(id=another_task_execution.id).count() == 1