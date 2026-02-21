from datetime import timedelta
from django.utils import timezone
import pytest
from processes.models import (
    TaskExecution,
    DelayedTaskExecutionStartEvent,
    MissingHeartbeatDetectionEvent,
    Execution
)
from processes.services.task_execution_checker import TaskExecutionChecker

@pytest.mark.django_db
class TestTaskExecutionChecker:
    @pytest.fixture
    def checker(self):
        return TaskExecutionChecker()

    def test_check_started_on_time_too_late(self, checker, task_factory, task_execution_factory):
        utc_now = timezone.now()
        task = task_factory(max_manual_start_delay_before_alert_seconds=60)
        te = task_execution_factory(
            task=task,
            status=Execution.Status.MANUALLY_STARTED,
            started_at=utc_now - timedelta(seconds=70),
            created_at=utc_now - timedelta(seconds=80)
        )

        checker.check_task_execution(te)

        te.refresh_from_db()
        assert te.status == Execution.Status.MANUALLY_STARTED
        assert DelayedTaskExecutionStartEvent.objects.filter(task_execution=te).count() == 1

    def test_check_started_on_time_abandoned(self, checker, task_factory, task_execution_factory):
        utc_now = timezone.now()
        task = task_factory(max_manual_start_delay_before_abandonment_seconds=120)
        te = task_execution_factory(
            task=task,
            status=Execution.Status.MANUALLY_STARTED,
            started_at=utc_now - timedelta(seconds=130),
            created_at=utc_now - timedelta(seconds=140)
        )

        checker.check_task_execution(te)

        te.refresh_from_db()
        assert te.status == Execution.Status.ABANDONED
        assert te.stop_reason == TaskExecution.StopReason.FAILED_TO_START
        assert te.marked_done_at is not None

    def test_check_timeout_max_age(self, checker, task_factory, task_execution_factory):
        utc_now = timezone.now()
        task = task_factory(max_age_seconds=300)
        te = task_execution_factory(
            task=task,
            status=Execution.Status.RUNNING,
            started_at=utc_now - timedelta(seconds=310)
        )

        checker.check_task_execution(te)

        te.refresh_from_db()
        assert te.status == Execution.Status.STOPPING
        assert te.stop_reason == TaskExecution.StopReason.MAX_EXECUTION_TIME_EXCEEDED
        assert te.marked_done_at is not None
        assert te.finished_at is None  # Should be set by the task later

    def test_check_timeout_stopping_too_long(self, checker, task_factory, task_execution_factory):
        utc_now = timezone.now()
        task = task_factory()
        te = task_execution_factory(
            task=task,
            status=Execution.Status.STOPPING,
            started_at=utc_now - timedelta(seconds=checker.MAX_STOPPING_DURATION_SECONDS + 10)
        )

        checker.check_task_execution(te)

        te.refresh_from_db()
        assert te.status == Execution.Status.ABANDONED
        assert te.marked_done_at is not None
        assert te.finished_at is not None

    def test_check_missing_heartbeat_alert(self, checker, task_factory, task_execution_factory):
        utc_now = timezone.now()
        task = task_factory(max_heartbeat_lateness_before_alert_seconds=30)
        te = task_execution_factory(
            task=task,
            status=Execution.Status.RUNNING,
            started_at=utc_now - timedelta(seconds=200),
            heartbeat_interval_seconds=60,
            last_heartbeat_at=utc_now - timedelta(seconds=100)  # 100 > 60 + 30
        )

        checker.check_task_execution(te)

        te.refresh_from_db()
        assert te.status == Execution.Status.RUNNING
        assert MissingHeartbeatDetectionEvent.objects.filter(task_execution=te).count() == 1

    def test_check_missing_heartbeat_abandoned(self, checker, task_factory, task_execution_factory):
        utc_now = timezone.now()
        task = task_factory(max_heartbeat_lateness_before_abandonment_seconds=120)
        te = task_execution_factory(
            task=task,
            status=Execution.Status.RUNNING,
            started_at=utc_now - timedelta(seconds=300),
            heartbeat_interval_seconds=60,
            last_heartbeat_at=utc_now - timedelta(seconds=200)  # 200 > 60 + 120
        )

        checker.check_task_execution(te)

        te.refresh_from_db()
        assert te.status == Execution.Status.ABANDONED
        assert te.stop_reason == TaskExecution.StopReason.MISSING_HEARTBEAT
        assert te.marked_done_at is not None
        assert te.finished_at is not None

    def test_check_missing_heartbeat_not_alert_eligible_started_before_service_update(self, checker, task_factory, task_execution_factory):
        utc_now = timezone.now()
        service_updated_at = utc_now - timedelta(seconds=50)
        task = task_factory(
            max_heartbeat_lateness_before_abandonment_seconds=10,
            aws_ecs_service_updated_at=service_updated_at
        )
        te = task_execution_factory(
            task=task,
            status=Execution.Status.RUNNING,
            started_at=utc_now - timedelta(seconds=100), # started before service updated
            heartbeat_interval_seconds=30,
            last_heartbeat_at=utc_now - timedelta(seconds=80) 
        )

        checker.check_task_execution(te)

        te.refresh_from_db()
        # Should still be abandoned because of missing heartbeat, but skip_event_generation should be True
        assert te.status == Execution.Status.ABANDONED
        assert te.skip_event_generation is True

    def test_check_missing_heartbeat_expected_at_shifted_by_service_update(self, checker, task_factory, task_execution_factory):
        utc_now = timezone.now()
        last_heartbeat_at = utc_now - timedelta(seconds=100)
        service_updated_at = utc_now - timedelta(seconds=80) # > last_heartbeat_at
        
        task = task_factory(
            max_heartbeat_lateness_before_alert_seconds=10,
            max_heartbeat_lateness_before_abandonment_seconds=20,
            aws_ecs_service_updated_at=service_updated_at
        )
        te = task_execution_factory(
            task=task,
            status=Execution.Status.RUNNING,
            started_at=utc_now - timedelta(seconds=200),
            heartbeat_interval_seconds=60,
            last_heartbeat_at=last_heartbeat_at
        )
    
        # expected_heartbeat_at = service_updated_at + 60 = -80 + 60 = -20s from now
        # lateness_before_abandonment = 20
        # -20 + 20 = 0 <= 0 (utc_now), so it should trigger abandonment.
    
        checker.check_task_execution(te)
    
        te.refresh_from_db()
        assert te.status == Execution.Status.ABANDONED
        assert te.stop_reason == TaskExecution.StopReason.MISSING_HEARTBEAT
        assert MissingHeartbeatDetectionEvent.objects.filter(task_execution=te).count() == 0

    def test_check_all(self, checker, task_factory, task_execution_factory):
        utc_now = timezone.now()
        task = task_factory(max_age_seconds=100)
        te1 = task_execution_factory(
            task=task,
            status=Execution.Status.RUNNING,
            started_at=utc_now - timedelta(seconds=150)
        )
        
        # Should be checked
        te2 = task_execution_factory(
            task=task,
            status=Execution.Status.MANUALLY_STARTED,
            started_at=utc_now - timedelta(seconds=150)
        )
        
        # Should NOT be checked (already finished)
        te3 = task_execution_factory(
            task=task,
            status=Execution.Status.SUCCEEDED,
            started_at=utc_now - timedelta(seconds=150),
            finished_at=utc_now - timedelta(seconds=50)
        )

        checker.check_all()

        te1.refresh_from_db()
        te2.refresh_from_db()
        te3.refresh_from_db()

        assert te1.status == Execution.Status.STOPPING
        assert te2.status == Execution.Status.STOPPING # It also checks timeout after started_on_time
        assert te3.status == Execution.Status.SUCCEEDED
