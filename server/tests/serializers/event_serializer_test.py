from django.utils import timezone

from processes.models import (
    Event,
    MissingHeartbeatDetectionEvent,
    MissingScheduledTaskExecutionEvent,
    MissingScheduledWorkflowExecutionEvent,
    DelayedTaskExecutionStartEvent,
    UserGroupAccessLevel
)

import pytest

from conftest import *


@pytest.mark.django_db
def test_event_polymorphic_serialization(
        user_factory, run_environment_factory,
        task_factory, task_execution_factory,
        workflow_factory, workflow_execution_factory,
        basic_event_factory,
        task_execution_status_change_event_factory,
        workflow_execution_status_change_event_factory,
        insufficient_service_task_executions_event_factory,
        delayed_task_execution_start_event_factory,
        api_client) -> None:
    """
    Test that the API correctly returns different event types with their specific fields.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create events of different types
    basic_event = basic_event_factory(created_by_group=group)
    task_event = task_execution_status_change_event_factory(created_by_group=group)
    workflow_event = workflow_execution_status_change_event_factory(created_by_group=group)
    insufficient_event = insufficient_service_task_executions_event_factory(created_by_group=group)
    
    # Create MissingHeartbeatDetectionEvent
    from datetime import timedelta
    from django.utils import timezone
    now = timezone.now()
    task = task_factory(created_by_group=group)
    task_execution = task_execution_factory(task=task)
    heartbeat_event = MissingHeartbeatDetectionEvent.objects.create(
        created_by_group=group,
        task=task,
        task_execution=task_execution,
        last_heartbeat_at=now - timedelta(minutes=10),
        expected_heartbeat_at=now - timedelta(minutes=5),
        heartbeat_interval_seconds=300,
        severity=Event.Severity.ERROR.value
    )
    
    # Create MissingScheduledTaskExecutionEvent
    scheduled_task = task_factory(created_by_group=group)
    scheduled_task_event = MissingScheduledTaskExecutionEvent.objects.create(
        created_by_group=group,
        task=scheduled_task,
        schedule="0 12 * * *",
        expected_execution_at=now,
        severity=Event.Severity.ERROR.value
    )
    
    # Create MissingScheduledWorkflowExecutionEvent
    workflow = workflow_factory(created_by_group=group)
    scheduled_workflow_event = MissingScheduledWorkflowExecutionEvent.objects.create(
        created_by_group=group,
        workflow=workflow,
        schedule="0 12 * * *",
        expected_execution_at=now,
        severity=Event.Severity.ERROR.value
    )
    
    # Create DelayedTaskExecutionStartEvent
    delayed_task = task_factory(created_by_group=group)
    delayed_task_execution = task_execution_factory(task=delayed_task)
    delayed_event = delayed_task_execution_start_event_factory(
        created_by_group=group,
        task=delayed_task,
        task_execution=delayed_task_execution
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test list endpoint returns correct event types
    response = client.get('/api/v1/events/')
    assert response.status_code == 200

    print(f"response.data: '{response.data}'")

    results = response.data['results']
    assert len(results) == 8

    # Map events by UUID for validation
    events_by_uuid = {
        str(basic_event.uuid): basic_event,
        str(task_event.uuid): task_event,
        str(workflow_event.uuid): workflow_event,
        str(insufficient_event.uuid): insufficient_event,
        str(heartbeat_event.uuid): heartbeat_event,
        str(scheduled_task_event.uuid): scheduled_task_event,
        str(scheduled_workflow_event.uuid): scheduled_workflow_event,
        str(delayed_event.uuid): delayed_event,
    }

    # Check that each event has correct event_type and validate thoroughly
    for result in results:
        event = events_by_uuid[result['uuid']]
        ensure_serialized_event_valid(
            result,
            event,
            user,
            UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
        )

    # Verify specific event types
    event_types = {r['uuid']: r['event_type'] for r in results}
    assert event_types[str(basic_event.uuid)] == 'basic'
    assert event_types[str(task_event.uuid)] == 'task_execution_status_change'
    assert event_types[str(workflow_event.uuid)] == 'workflow_execution_status_change'
    assert event_types[str(insufficient_event.uuid)] == 'insufficient_service_task_executions'
    assert event_types[str(heartbeat_event.uuid)] == 'missing_heartbeat_detection'
    assert event_types[str(scheduled_task_event.uuid)] == 'missing_scheduled_task_execution'
    assert event_types[str(scheduled_workflow_event.uuid)] == 'missing_scheduled_workflow_execution'
    assert event_types[str(delayed_event.uuid)] == 'delayed_task_execution_start'

    # Test retrieve endpoint for TaskExecutionStatusChangeEvent
    response = client.get(f'/api/v1/events/{task_event.uuid}/')
    assert response.status_code == 200
    ensure_serialized_event_valid(
        response.data,
        task_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
    assert response.data['event_type'] == 'task_execution_status_change'
    assert 'task' in response.data
    assert 'task_execution' in response.data

    # Test retrieve endpoint for WorkflowExecutionStatusChangeEvent
    response = client.get(f'/api/v1/events/{workflow_event.uuid}/')
    assert response.status_code == 200
    ensure_serialized_event_valid(
        response.data,
        workflow_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
    assert response.data['event_type'] == 'workflow_execution_status_change'
    assert 'workflow' in response.data
    assert 'workflow_execution' in response.data

    # Test retrieve endpoint for InsufficientServiceTaskExecutionsEvent
    response = client.get(f'/api/v1/events/{insufficient_event.uuid}/')
    assert response.status_code == 200
    ensure_serialized_event_valid(
        response.data,
        insufficient_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
    assert response.data['event_type'] == 'insufficient_service_task_executions'
    assert 'task' in response.data
    assert 'interval_start_at' in response.data
    assert 'interval_end_at' in response.data
    assert 'detected_concurrency' in response.data
    assert 'required_concurrency' in response.data

    # Test retrieve endpoint for MissingHeartbeatDetectionEvent
    response = client.get(f'/api/v1/events/{heartbeat_event.uuid}/')
    assert response.status_code == 200
    ensure_serialized_event_valid(
        response.data,
        heartbeat_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
    assert response.data['event_type'] == 'missing_heartbeat_detection'
    assert 'task' in response.data
    assert 'last_heartbeat_at' in response.data
    assert 'expected_heartbeat_at' in response.data
    assert 'heartbeat_interval_seconds' in response.data

    # Test retrieve endpoint for MissingScheduledTaskExecutionEvent
    response = client.get(f'/api/v1/events/{scheduled_task_event.uuid}/')
    assert response.status_code == 200
    ensure_serialized_event_valid(
        response.data,
        scheduled_task_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
    assert response.data['event_type'] == 'missing_scheduled_task_execution'
    assert 'task' in response.data
    assert 'schedule' in response.data
    assert 'expected_execution_at' in response.data

    # Test retrieve endpoint for MissingScheduledWorkflowExecutionEvent
    response = client.get(f'/api/v1/events/{scheduled_workflow_event.uuid}/')
    assert response.status_code == 200
    ensure_serialized_event_valid(
        response.data,
        scheduled_workflow_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
    assert response.data['event_type'] == 'missing_scheduled_workflow_execution'
    assert 'workflow' in response.data
    assert 'schedule' in response.data
    assert 'expected_execution_at' in response.data

    # Test retrieve endpoint for DelayedTaskExecutionStartEvent
    response = client.get(f'/api/v1/events/{delayed_event.uuid}/')
    assert response.status_code == 200
    ensure_serialized_event_valid(
        response.data,
        delayed_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
    assert response.data['event_type'] == 'delayed_task_execution_start'
    assert 'task' in response.data
    assert 'task_execution' in response.data
    assert 'desired_start_at' in response.data
    assert 'expected_start_by_deadline' in response.data


@pytest.mark.django_db
def test_patch_acknowledged_sets_and_clears_user(
        user_factory, basic_event_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    # give user sufficient access
    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    event = basic_event_factory(created_by_group=group)

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=None, api_key_run_environment=None)

    # Acknowledge the event
    ts = timezone.now().isoformat()
    url = f'/api/v1/events/{event.uuid}/'
    response = client.patch(url, data={'acknowledged_at': ts}, format='json')
    assert response.status_code == 200

    event.refresh_from_db()
    assert event.acknowledged_at is not None
    assert event.acknowledged_by_user is not None
    assert event.acknowledged_by_user.pk == user.pk

    # Clear the acknowledgment
    response = client.patch(url, data={'acknowledged_at': None}, format='json')
    assert response.status_code == 200
    event.refresh_from_db()
    assert event.acknowledged_at is None
    assert event.acknowledged_by_user is None


@pytest.mark.django_db
def test_patch_resolved_sets_and_clears_user(
        user_factory, basic_event_factory, api_client):
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    event = basic_event_factory(created_by_group=group)

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=None, api_key_run_environment=None)

    ts = timezone.now().isoformat()
    url = f'/api/v1/events/{event.uuid}/'
    response = client.patch(url, data={'resolved_at': ts}, format='json')
    assert response.status_code == 200

    event.refresh_from_db()
    assert event.resolved_at is not None
    assert event.resolved_by_user is not None
    assert event.resolved_by_user.pk == user.pk

    # Clear the resolution
    response = client.patch(url, data={'resolved_at': None}, format='json')
    assert response.status_code == 200
    event.refresh_from_db()
    assert event.resolved_at is None
    assert event.resolved_by_user is None
