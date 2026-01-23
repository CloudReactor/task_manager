from datetime import timedelta

import logging

from django.utils import timezone

from processes.models import (
    InsufficientServiceTaskExecutionsEvent
)

from processes.services.service_concurrency_checker import (
    ServiceConcurrencyChecker,
    LOOKBACK_DURATION_SECONDS
)

import pytest

from moto import mock_aws


logger = logging.getLogger(__name__)


@pytest.mark.django_db
@pytest.mark.parametrize("""
    enabled,
    min_instance_count,
    running_instances,
    expected_event
""", [
    # Sufficient instances
    (True, 2, 2, False),
    (True, 2, 3, False),
    
    # Insufficient instances
    (True, 2, 1, True),
    (True, 3, 2, True),
    (True, 1, 0, True),
    
    # Disabled service
    (False, 2, 1, False),
    
    # No min instance count set
    (True, 0, 0, False),
    (True, None, 0, False),
])
@mock_aws
def test_service_concurrency_checker_basic(
        enabled: bool,
        min_instance_count: int | None,
        running_instances: int,
        expected_event: bool,
        task_factory,
        task_execution_factory):
    """Test basic concurrency checking with various instance counts."""
    utc_now = timezone.now()
    start_time = utc_now - timedelta(minutes=10)
    
    # Create a service task
    service = task_factory(
        enabled=enabled,
        min_service_instance_count=min_instance_count
    )

    before = utc_now - timedelta(hours=1)
    service.created_at = before
    service.updated_at = before
    service.save()
    
    # Create running task executions
    for i in range(running_instances):
        task_execution_factory(
            task=service,
            started_at=start_time,
            finished_at=None,
            marked_done_at=None,
            kill_started_at=None
        )
    
    checker = ServiceConcurrencyChecker()
    checker.check_all()
    
    events = InsufficientServiceTaskExecutionsEvent.objects.filter(
        task=service,
        resolved_at__isnull=True
    )
    
    if expected_event:
        assert events.count() == 1
        event = events.first()
        assert event is not None
        assert event.detected_concurrency == running_instances
        assert event.required_concurrency == min_instance_count
        assert event.interval_start_at is not None
        assert event.interval_end_at is not None
        assert event.resolved_at is None
    else:
        assert events.count() == 0


@pytest.mark.django_db
@mock_aws
def test_service_concurrency_checker_with_finished_executions(
        task_factory,
        task_execution_factory):
    """Test that finished executions are not counted in current concurrency."""
    utc_now = timezone.now()
    start_time = utc_now - timedelta(minutes=10)
    
    service = task_factory(
        enabled=True,
        min_service_instance_count=2
    )
    
    before = utc_now - timedelta(hours=1)
    service.created_at = before
    service.updated_at = before
    service.save()

    # Create 1 running execution
    task_execution_factory(
        task=service,
        started_at=start_time,
        finished_at=None,
        marked_done_at=None,
        kill_started_at=None
    )
    
    # Create 2 finished executions (should not count)
    for i in range(2):
        task_execution_factory(
            task=service,
            started_at=start_time - timedelta(minutes=5),
            finished_at=start_time - timedelta(minutes=2),
            marked_done_at=None,
            kill_started_at=None
        )
    
    checker = ServiceConcurrencyChecker()
    checker.check_all()
    
    events = InsufficientServiceTaskExecutionsEvent.objects.filter(
        task=service,
        resolved_at__isnull=True
    )
    
    assert events.count() == 1
    event = events.first()
    assert event.detected_concurrency == 1
    assert event.required_concurrency == 2


@pytest.mark.django_db
@mock_aws
def test_service_concurrency_checker_duplicate_event_prevention(
        task_factory,
        task_execution_factory):
    """Test that duplicate events are not created if one already exists."""
    utc_now = timezone.now()
    start_time = utc_now - timedelta(minutes=10)
    
    service = task_factory(
        enabled=True,
        min_service_instance_count=2
    )
    

    before = utc_now - timedelta(hours=1)
    service.created_at = before
    service.updated_at = before
    service.save()
        
    # Create 1 running execution (insufficient)
    task_execution_factory(
        task=service,
        started_at=start_time,
        finished_at=None,
        marked_done_at=None,
        kill_started_at=None
    )
    
    checker = ServiceConcurrencyChecker()
    
    # First check - should create event
    checker.check_all()
    events = InsufficientServiceTaskExecutionsEvent.objects.filter(task=service)
    assert events.count() == 1
    first_event = events.first()
    
    # Second check - should not create duplicate
    checker.check_service(service)
    events = InsufficientServiceTaskExecutionsEvent.objects.filter(task=service)
    assert events.count() == 1
    second_event = events.first()
    assert first_event.uuid == second_event.uuid


@pytest.mark.django_db
@mock_aws
def test_service_concurrency_checker_event_resolution(
        task_factory,
        task_execution_factory):
    """Test that events are resolved when concurrency becomes sufficient."""
    utc_now = timezone.now()
    start_time = utc_now - timedelta(minutes=10)
    
    service = task_factory(
        enabled=True,
        min_service_instance_count=2
    )

    before = utc_now - timedelta(hours=1)
    service.created_at = before
    service.updated_at = before
    service.save()

    # Create 1 running execution (insufficient)
    te1 = task_execution_factory(
        task=service,
        started_at=start_time,
        finished_at=None,
        marked_done_at=None,
        kill_started_at=None
    )
    
    checker = ServiceConcurrencyChecker()
    
    # First check - should create event
    checker.check_all()
    events = InsufficientServiceTaskExecutionsEvent.objects.filter(
        task=service,
        resolved_at__isnull=True
    )
    assert events.count() == 1
    original_event = events.first()
    
    # Add another execution to bring concurrency to sufficient level
    # Use the same start time as te1 to ensure concurrency is sufficient across the entire lookback window
    te2 = task_execution_factory(
        task=service,
        started_at=start_time,
        finished_at=None,
        marked_done_at=None,
        kill_started_at=None
    )
    
    # Second check - should resolve the event
    checker.check_all()
    
    # Original event should now be resolved
    original_event.refresh_from_db()
    assert original_event.resolved_at is not None
    
    # Should have a resolving event
    all_events = InsufficientServiceTaskExecutionsEvent.objects.filter(task=service)
    assert all_events.count() == 2
    
    resolving_event = all_events.filter(resolved_event=original_event).first()
    assert resolving_event is not None
    assert resolving_event.detected_concurrency == 2
    assert resolving_event.required_concurrency == 2
    assert resolving_event.resolved_at is not None


@pytest.mark.django_db
@mock_aws
def test_service_concurrency_checker_lookback_window(
        task_factory,
        task_execution_factory):
    """Test that only executions within the lookback window are considered."""
    utc_now = timezone.now()
    lookback_start = utc_now - timedelta(seconds=LOOKBACK_DURATION_SECONDS)
    
    service = task_factory(
        enabled=True,
        min_service_instance_count=1,
    )

    before = utc_now - timedelta(hours=1)
    service.created_at = before
    service.updated_at = before
    service.save()

    # Create an execution that finished before the lookback window
    task_execution_factory(
        task=service,
        started_at=lookback_start - timedelta(minutes=10),
        finished_at=lookback_start - timedelta(minutes=5),
        marked_done_at=None,
        kill_started_at=None
    )
    
    checker = ServiceConcurrencyChecker()
    checker.check_service(service)
    
    # Should detect insufficient concurrency since old execution doesn't count
    events = InsufficientServiceTaskExecutionsEvent.objects.filter(
        task=service,
        resolved_at__isnull=True
    )
    assert events.count() == 1
    event = events.first()
    assert event.detected_concurrency == 0


@pytest.mark.django_db
@mock_aws
def test_service_concurrency_checker_startup_delay(
        task_factory,
        task_execution_factory):
    """Test that services are not checked until after startup delay."""
    utc_now = timezone.now()
    
    # Create a service that was just created
    service = task_factory(
        enabled=True,
        min_service_instance_count=2,
        max_manual_start_delay_before_alert_seconds=300,
        created_at=utc_now - timedelta(seconds=60)  # Created 1 minute ago
    )
    
    checker = ServiceConcurrencyChecker()
    checker.check_all()
    
    # Should not create an event because service is still within startup delay
    events = InsufficientServiceTaskExecutionsEvent.objects.filter(task=service)
    assert events.count() == 0


@pytest.mark.django_db
@mock_aws
def test_service_concurrency_checker_check_all(
        task_factory,
        task_execution_factory):
    """Test check_all method processes all enabled services."""
    utc_now = timezone.now()
    start_time = utc_now - timedelta(minutes=10)
    
    # Create multiple services
    service1 = task_factory(
        enabled=True,
        min_service_instance_count=2
    )

    service2 = task_factory(
        enabled=True,
        min_service_instance_count=1
    )
    
    # Service 3 is disabled, should be ignored
    service3 = task_factory(
        enabled=False,
        min_service_instance_count=2
    )
    
    # Service 4 has no min_service_instance_count, should be ignored
    service4 = task_factory(
        enabled=True,
        min_service_instance_count=None
    )

    for service in [service1, service2, service3, service4]:
        before = utc_now - timedelta(hours=1)
        service.created_at = before
        service.updated_at = before
        service.save()

    # Add insufficient executions for service1 (1 running, needs 2)
    task_execution_factory(
        task=service1,
        started_at=start_time,
        finished_at=None,
        marked_done_at=None,
        kill_started_at=None
    )
    
    # Service2 has no executions (0 running, needs 1)
    
    checker = ServiceConcurrencyChecker()
    checker.check_all()
    
    # Check service1 has event
    events1 = InsufficientServiceTaskExecutionsEvent.objects.filter(
        task=service1,
        resolved_at__isnull=True
    )
    assert events1.count() == 1
    assert events1.first().detected_concurrency == 1
    
    # Check service2 has event
    events2 = InsufficientServiceTaskExecutionsEvent.objects.filter(
        task=service2,
        resolved_at__isnull=True
    )
    assert events2.count() == 1
    assert events2.first().detected_concurrency == 0
    
    # Check service3 has no event (disabled)
    events3 = InsufficientServiceTaskExecutionsEvent.objects.filter(task=service3)
    assert events3.count() == 0
    
    # Check service4 has no event (no min count)
    events4 = InsufficientServiceTaskExecutionsEvent.objects.filter(task=service4)
    assert events4.count() == 0


@pytest.mark.django_db
@mock_aws
def test_service_concurrency_checker_interval_timestamps(task_factory):
    """Test that interval timestamps are correctly set without microseconds."""
    utc_now = timezone.now()
    
    service = task_factory(
        enabled=True,
        min_service_instance_count=1
    )
    
    before = utc_now - timedelta(hours=1)
    service.created_at = before
    service.updated_at = before
    service.save()

    # Don't create any executions - insufficient concurrency
    
    checker = ServiceConcurrencyChecker()
    checker.check_all()
    
    events = InsufficientServiceTaskExecutionsEvent.objects.filter(task=service)
    assert events.count() == 1
    
    event = events.first()
    # Check that microseconds are set to 0
    assert event.interval_start_at.microsecond == 0
    assert event.interval_end_at.microsecond == 0
    
    # Check that interval_start and interval_end are reasonable
    assert event.interval_start_at <= event.interval_end_at
    
    # Allow some tolerance for execution time
    time_diff = abs((event.interval_end_at - utc_now).total_seconds())
    assert time_diff < 5  # Within 5 seconds
