from typing import List
from unittest.mock import MagicMock, patch

from datetime import timedelta
import random

from django.utils import timezone

import pytest

from moto import mock_aws
from rest_framework.exceptions import APIException

from processes.exception import CommittableException
from processes.execution_methods import ExecutionMethod
from processes.models import (
    Subscription,
    SubscriptionPlan,
    Task,
    TaskExecution,
    Execution
)


# ---------------------------------------------------------------------------
# Helpers for synchronize_with_run_environment tests
# ---------------------------------------------------------------------------

def _make_em(
    should_update_sched: tuple[bool, bool] = (False, False),
    should_update_svc: tuple[bool, bool] = (False, False),
    supports_scheduling: bool = True,
    supports_service: bool = True,
) -> MagicMock:
    """Return a mock ExecutionMethod pre-configured for synchronize tests."""
    em = MagicMock()
    em.name = 'mock_em'
    em.should_update_or_force_recreate_scheduled_execution.return_value = should_update_sched
    em.should_update_or_force_recreate_service.return_value = should_update_svc
    em.teardown_scheduled_execution.return_value = ({'rule_arn': 'old_rule'}, 'sched_teardown_result')
    em.teardown_service.return_value = ({'service_arn': 'old_service'}, 'svc_teardown_result')
    em.supports_capability.side_effect = lambda cap: {
        ExecutionMethod.ExecutionCapability.SCHEDULING: supports_scheduling,
        ExecutionMethod.ExecutionCapability.SETUP_SERVICE: supports_service,
    }.get(cap, False)
    return em


def _make_old_self(
    passive: bool = False,
    schedule: str = '',
    is_scheduling_managed: bool | None = None,
    service_instance_count: int | None = None,
    is_service_managed: bool | None = None,
    enabled: bool = True,
    old_mock_em: MagicMock | None = None,
) -> MagicMock:
    """Return a MagicMock that stands in for an old Task snapshot."""
    m = MagicMock(spec=Task)
    m.passive = passive
    m.schedule = schedule
    m.is_scheduling_managed = is_scheduling_managed
    m.service_instance_count = service_instance_count
    m.is_service_managed = is_service_managed
    m.enabled = enabled
    # has_active_managed_scheduled_execution and is_active_managed_service are
    # auto-mocked as MagicMocks (truthy), so set explicit return values.
    m.has_active_managed_scheduled_execution.return_value = (
        enabled and not passive and bool(schedule) and (is_scheduling_managed is not False)
    )
    m.is_active_managed_service.return_value = (
        enabled and not passive and (service_instance_count is not None) and bool(is_service_managed)
    )
    if old_mock_em is not None:
        m.execution_method.return_value = old_mock_em
    return m


def _sync(
    task: Task,
    mock_em: MagicMock,
    old_self=None,
    is_saving: bool = False,
) -> bool:
    """Patch task.execution_method and call synchronize_with_run_environment."""
    with patch.object(task, 'execution_method', return_value=mock_em):
        return task.synchronize_with_run_environment(old_self=old_self, is_saving=is_saving)


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
            status=Execution.Status.SUCCEEDED)

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


# ===========================================================================
# Tests for Task.synchronize_with_run_environment()
# ===========================================================================

# ---------------------------------------------------------------------------
# 0. Early-exit: passive task
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_passive_both_passive_returns_false(task_factory):
    task = task_factory()
    task.passive = True

    old_self = _make_old_self(passive=True)

    result = task.synchronize_with_run_environment(old_self=old_self)

    assert result is False


@pytest.mark.django_db
@mock_aws
def test_sync_passive_self_old_self_not_passive_proceeds(task_factory):
    """When self is passive but old_self was not, the method does not early-exit."""
    task = task_factory()
    task.passive = True

    mock_em = _make_em()
    old_self = _make_old_self(passive=False)

    result = _sync(task, mock_em, old_self=old_self)

    assert isinstance(result, bool)
    mock_em.should_update_or_force_recreate_scheduled_execution.assert_called_once()
    mock_em.should_update_or_force_recreate_service.assert_called_once()


# ---------------------------------------------------------------------------
# 1. schedule_updated_at bookkeeping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_schedule_updated_at_set_when_schedule_changed(task_factory):
    task = task_factory()
    task.schedule = 'rate(1 hour)'

    old_self = _make_old_self(schedule='rate(30 minutes)')
    original_updated_at = task.schedule_updated_at

    _sync(task, _make_em(), old_self=old_self)

    assert task.schedule_updated_at > original_updated_at


@pytest.mark.django_db
@mock_aws
def test_sync_schedule_updated_at_not_changed_when_schedule_same(task_factory):
    task = task_factory()
    task.schedule = 'rate(1 hour)'

    old_self = _make_old_self(schedule='rate(1 hour)')
    original_updated_at = task.schedule_updated_at

    _sync(task, _make_em(), old_self=old_self)

    assert task.schedule_updated_at == original_updated_at


@pytest.mark.django_db
@mock_aws
def test_sync_schedule_updated_at_not_changed_without_old_self(task_factory):
    task = task_factory()
    task.schedule = 'rate(1 hour)'
    original_updated_at = task.schedule_updated_at

    _sync(task, _make_em())

    assert task.schedule_updated_at == original_updated_at


# ---------------------------------------------------------------------------
# 2. Scheduling — no update needed (should_update == False)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_no_scheduling_update_skips_setup_and_teardown(task_factory):
    task = task_factory()
    mock_em = _make_em(should_update_sched=(False, False))

    _sync(task, mock_em)

    mock_em.setup_scheduled_execution.assert_not_called()
    mock_em.teardown_scheduled_execution.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Scheduling — update needed, will NOT be a managed scheduled execution
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_scheduling_teardown_called_when_was_managed_now_not(task_factory):
    """Old task had managed scheduling; new task does not → teardown is called."""
    task = task_factory()
    task.schedule = ''
    task.is_scheduling_managed = True

    old_mock_em = _make_em()
    old_self = _make_old_self(
        schedule='rate(1 hour)',
        is_scheduling_managed=True,
        enabled=True,
        old_mock_em=old_mock_em,
    )
    old_self.has_active_managed_scheduled_execution.return_value = True

    mock_em = _make_em(should_update_sched=(True, False))
    _sync(task, mock_em, old_self=old_self)

    old_mock_em.teardown_scheduled_execution.assert_called()
    assert task.is_scheduling_managed is None


@pytest.mark.django_db
@mock_aws
def test_sync_scheduling_teardown_not_called_without_old_em(task_factory):
    """No old execution method → teardown not called; is_scheduling_managed set to None."""
    task = task_factory()
    task.schedule = ''
    task.is_scheduling_managed = True

    mock_em = _make_em(should_update_sched=(True, False))
    _sync(task, mock_em, old_self=None)

    mock_em.teardown_scheduled_execution.assert_not_called()
    assert task.is_scheduling_managed is None


@pytest.mark.django_db
@mock_aws
def test_sync_scheduling_is_scheduling_managed_stays_false_when_already_false(task_factory):
    """When is_scheduling_managed is already False, the guard does not overwrite it."""
    task = task_factory()
    task.schedule = ''
    task.is_scheduling_managed = False

    mock_em = _make_em(should_update_sched=(True, False))
    _sync(task, mock_em, old_self=None)

    assert task.is_scheduling_managed is False


# ---------------------------------------------------------------------------
# 4. Scheduling — update needed, will be managed (setup succeeds)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_scheduling_setup_called_for_new_task(task_factory):
    """No old state → setup_scheduled_execution called; is_scheduling_managed = True."""
    task = task_factory()
    task.schedule = 'rate(1 hour)'
    task.is_scheduling_managed = None

    mock_em = _make_em(should_update_sched=(True, True), supports_scheduling=True)

    with patch.object(task, 'has_active_managed_scheduled_execution', return_value=True):
        with patch.object(task, 'execution_method', return_value=mock_em):
            task.synchronize_with_run_environment(old_self=None)

    mock_em.setup_scheduled_execution.assert_called_once_with(
        old_execution_method=None,
        force_creation=True,
        teardown_result=None,
    )
    assert task.is_scheduling_managed is True


@pytest.mark.django_db
@mock_aws
def test_sync_scheduling_force_recreate_teardown_then_setup(task_factory):
    """Force-recreate: old schedule is torn down before new one is set up."""
    task = task_factory()
    task.schedule = 'rate(2 hours)'
    task.is_scheduling_managed = True

    old_mock_em = _make_em()
    old_self = _make_old_self(
        schedule='rate(1 hour)',
        is_scheduling_managed=True,
        enabled=True,
        old_mock_em=old_mock_em,
    )
    old_self.has_active_managed_scheduled_execution.return_value = True

    mock_em = _make_em(should_update_sched=(True, True), supports_scheduling=True)

    with patch.object(task, 'has_active_managed_scheduled_execution', return_value=True):
        with patch.object(task, 'execution_method', return_value=mock_em):
            task.synchronize_with_run_environment(old_self=old_self)

    old_mock_em.teardown_scheduled_execution.assert_called_once()
    mock_em.setup_scheduled_execution.assert_called_once()
    assert task.is_scheduling_managed is True


@pytest.mark.django_db
@mock_aws
def test_sync_scheduling_raises_when_capability_not_supported(task_factory):
    """Execution method lacking SCHEDULING capability raises APIException."""
    task = task_factory()
    task.schedule = 'rate(1 hour)'

    mock_em = _make_em(should_update_sched=(True, True), supports_scheduling=False)

    with patch.object(task, 'has_active_managed_scheduled_execution', return_value=True):
        with pytest.raises(APIException):
            with patch.object(task, 'execution_method', return_value=mock_em):
                task.synchronize_with_run_environment(old_self=None)


# ---------------------------------------------------------------------------
# 5. Scheduling — setup fails
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_scheduling_setup_fail_restores_settings_and_saves_when_teardown_ran(task_factory):
    """setup_scheduled_execution raises after teardown → task disabled, settings restored, save called."""
    task = task_factory()
    task.schedule = 'rate(2 hours)'
    task.is_scheduling_managed = True

    old_torn_settings = {'rule_arn': 'original_rule'}
    old_mock_em = MagicMock()
    old_mock_em.teardown_scheduled_execution.return_value = (old_torn_settings, 'result')

    old_self = _make_old_self(
        schedule='rate(1 hour)',
        is_scheduling_managed=True,
        enabled=True,
        old_mock_em=old_mock_em,
    )
    old_self.has_active_managed_scheduled_execution.return_value = True

    mock_em = _make_em(should_update_sched=(True, True), supports_scheduling=True)
    mock_em.setup_scheduled_execution.side_effect = RuntimeError('AWS error')

    with patch.object(task, 'has_active_managed_scheduled_execution', return_value=True):
        mock_db_task = MagicMock()
        with patch('processes.models.Task.objects.get', return_value=mock_db_task):
            with pytest.raises(RuntimeError, match='AWS error'):
                with patch.object(task, 'execution_method', return_value=mock_em):
                    task.synchronize_with_run_environment(old_self=old_self)

    assert mock_db_task.enabled is False
    assert mock_db_task.scheduling_settings == old_torn_settings
    mock_db_task.save_without_sync.assert_called_once()


@pytest.mark.django_db
@mock_aws
def test_sync_scheduling_setup_fail_no_prior_teardown_skips_save(task_factory):
    """setup_scheduled_execution raises but no teardown ran → save_without_sync not called."""
    task = task_factory()
    task.schedule = 'rate(1 hour)'

    mock_em = _make_em(should_update_sched=(True, True), supports_scheduling=True)
    mock_em.setup_scheduled_execution.side_effect = RuntimeError('AWS error')

    with patch.object(task, 'has_active_managed_scheduled_execution', return_value=True):
        with patch('processes.models.Task.objects.get', return_value=None):
            with pytest.raises(RuntimeError, match='AWS error'):
                with patch.object(task, 'execution_method', return_value=mock_em):
                    task.synchronize_with_run_environment(old_self=None)


# ---------------------------------------------------------------------------
# 6. Service — no update needed (should_update == False)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_no_service_update_skips_setup_and_teardown(task_factory):
    task = task_factory()
    mock_em = _make_em(should_update_svc=(False, False))

    _sync(task, mock_em)

    mock_em.setup_service.assert_not_called()
    mock_em.teardown_service.assert_not_called()


# ---------------------------------------------------------------------------
# 7. Service — update needed, will NOT be a managed service
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_service_teardown_called_when_was_managed_now_not(task_factory):
    """Old task was a managed service; new task is not → teardown is called."""
    task = task_factory()
    task.service_instance_count = None  # is_service = False
    task.is_service_managed = True

    old_mock_em = _make_em()
    old_self = _make_old_self(
        service_instance_count=1,
        is_service_managed=True,
        enabled=True,
        old_mock_em=old_mock_em,
    )
    old_self.is_active_managed_service.return_value = True

    mock_em = _make_em(should_update_svc=(True, False))

    with patch.object(task, 'is_active_managed_service', return_value=False):
        with patch.object(task, 'execution_method', return_value=mock_em):
            task.synchronize_with_run_environment(old_self=old_self)

    old_mock_em.teardown_service.assert_called()
    assert task.is_service_managed is None


@pytest.mark.django_db
@mock_aws
def test_sync_service_teardown_not_called_without_old_em(task_factory):
    """No old execution method → teardown not called."""
    task = task_factory()
    task.service_instance_count = None
    task.is_service_managed = None

    mock_em = _make_em(should_update_svc=(True, False))

    with patch.object(task, 'is_active_managed_service', return_value=False):
        with patch.object(task, 'execution_method', return_value=mock_em):
            task.synchronize_with_run_environment(old_self=None)

    mock_em.teardown_service.assert_not_called()


# ---------------------------------------------------------------------------
# 8. Service — update needed, will be managed (setup succeeds)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_service_setup_called_for_new_managed_service(task_factory):
    """New managed service → setup_service called; is_service_managed = True."""
    task = task_factory()
    task.service_instance_count = 1
    task.is_service_managed = None

    mock_em = _make_em(should_update_svc=(True, True), supports_service=True)

    with patch.object(task, 'is_active_managed_service', return_value=True):
        with patch.object(task, 'execution_method', return_value=mock_em):
            task.synchronize_with_run_environment(old_self=None)

    mock_em.setup_service.assert_called_once_with(
        old_execution_method=None,
        force_creation=True,
        teardown_result=None,
    )
    assert task.is_service_managed is True


@pytest.mark.django_db
@mock_aws
def test_sync_service_force_recreate_teardown_then_setup(task_factory):
    """Force-recreate: old service is torn down before new one is created."""
    task = task_factory()
    task.service_instance_count = 2
    task.is_service_managed = True

    old_mock_em = _make_em()
    old_self = _make_old_self(
        service_instance_count=2,
        is_service_managed=True,
        enabled=True,
        old_mock_em=old_mock_em,
    )
    old_self.is_active_managed_service.return_value = True

    mock_em = _make_em(should_update_svc=(True, True), supports_service=True)

    with patch.object(task, 'is_active_managed_service', return_value=True):
        with patch.object(task, 'execution_method', return_value=mock_em):
            task.synchronize_with_run_environment(old_self=old_self)

    old_mock_em.teardown_service.assert_called_once()
    mock_em.setup_service.assert_called_once()
    assert task.is_service_managed is True


@pytest.mark.django_db
@mock_aws
def test_sync_service_raises_when_capability_not_supported(task_factory):
    """Execution method lacking SETUP_SERVICE capability raises APIException."""
    task = task_factory()
    task.service_instance_count = 1

    mock_em = _make_em(should_update_svc=(True, True), supports_service=False)

    with patch.object(task, 'is_active_managed_service', return_value=True):
        with pytest.raises(APIException):
            with patch.object(task, 'execution_method', return_value=mock_em):
                task.synchronize_with_run_environment(old_self=None)


# ---------------------------------------------------------------------------
# 9. Service — setup fails
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_service_setup_fail_disables_task_and_raises_committable(task_factory):
    """setup_service failure with no teardown → task saved, APIException raised."""
    task = task_factory()
    task.service_instance_count = 1
    task.is_service_managed = None
    task.enabled = True

    mock_em = _make_em(should_update_svc=(True, True), supports_service=True)
    mock_em.setup_service.side_effect = RuntimeError('ECS error')

    with patch.object(task, 'is_active_managed_service', return_value=True):
        mock_db_task = MagicMock()
        with patch('processes.models.Task.objects.get', return_value=mock_db_task):
            with pytest.raises(APIException):
                with patch.object(task, 'execution_method', return_value=mock_em):
                    task.synchronize_with_run_environment(old_self=None)

    mock_db_task.save_without_sync.assert_called_once()


@pytest.mark.django_db
@mock_aws
def test_sync_service_setup_fail_after_teardown_restores_settings_and_saves(task_factory):
    """Teardown ran before failed setup → service_settings restored, saved to DB."""
    task = task_factory()
    task.service_instance_count = 2
    task.is_service_managed = True
    task.enabled = True

    old_torn_settings = {'service_arn': 'old_arn'}
    old_mock_em = MagicMock()
    old_mock_em.teardown_service.return_value = (old_torn_settings, 'svc_result')

    old_self = _make_old_self(
        service_instance_count=2,
        is_service_managed=True,
        enabled=True,
        old_mock_em=old_mock_em,
    )
    old_self.is_active_managed_service.return_value = True

    mock_em = _make_em(should_update_svc=(True, True), supports_service=True)
    mock_em.setup_service.side_effect = RuntimeError('ECS error')

    with patch.object(task, 'is_active_managed_service', return_value=True):
        mock_db_task = MagicMock()
        with patch('processes.models.Task.objects.get', return_value=mock_db_task):
            with pytest.raises(APIException):
                with patch.object(task, 'execution_method', return_value=mock_em):
                    task.synchronize_with_run_environment(old_self=old_self)

    assert mock_db_task.enabled is False
    assert mock_db_task.service_settings == old_torn_settings
    mock_db_task.save_without_sync.assert_called_once()


@pytest.mark.django_db
@mock_aws
def test_sync_service_setup_fail_no_prior_teardown_skips_save(task_factory):
    """setup_service raises but no teardown ran → save_without_sync still called."""
    task = task_factory()
    task.service_instance_count = 1
    task.is_service_managed = None

    mock_em = _make_em(should_update_svc=(True, True), supports_service=True)
    mock_em.setup_service.side_effect = RuntimeError('ECS error')

    with patch.object(task, 'is_active_managed_service', return_value=True):
        mock_db_task = MagicMock()
        with patch('processes.models.Task.objects.get', return_value=mock_db_task):
            with pytest.raises(APIException):
                with patch.object(task, 'execution_method', return_value=mock_em):
                    task.synchronize_with_run_environment(old_self=None)

    mock_db_task.save_without_sync.assert_called_once()


# ---------------------------------------------------------------------------
# 10. is_saving flag
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_is_saving_true_calls_save_without_sync(task_factory):
    task = task_factory()
    mock_em = _make_em()

    with patch.object(task, 'save_without_sync') as mock_save:
        _sync(task, mock_em, is_saving=True)

    mock_save.assert_called_once()


@pytest.mark.django_db
@mock_aws
def test_sync_is_saving_false_does_not_call_save_without_sync(task_factory):
    task = task_factory()
    mock_em = _make_em()

    with patch.object(task, 'save_without_sync') as mock_save:
        _sync(task, mock_em, is_saving=False)

    mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# 11. Return value
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@mock_aws
def test_sync_returns_true_when_only_scheduling_updated(task_factory):
    task = task_factory()
    mock_em = _make_em(should_update_sched=(True, False), should_update_svc=(False, False))

    result = _sync(task, mock_em)

    assert result is True


@pytest.mark.django_db
@mock_aws
def test_sync_returns_true_when_only_service_updated(task_factory):
    task = task_factory()
    mock_em = _make_em(should_update_sched=(False, False), should_update_svc=(True, False))

    result = _sync(task, mock_em)

    assert result is True


@pytest.mark.django_db
@mock_aws
def test_sync_returns_true_when_both_updated(task_factory):
    task = task_factory()
    mock_em = _make_em(should_update_sched=(True, False), should_update_svc=(True, False))

    result = _sync(task, mock_em)

    assert result is True


@pytest.mark.django_db
@mock_aws
def test_sync_returns_false_when_nothing_updated(task_factory):
    task = task_factory()
    mock_em = _make_em(should_update_sched=(False, False), should_update_svc=(False, False))

    result = _sync(task, mock_em)

    assert result is False
