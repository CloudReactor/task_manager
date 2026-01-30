from processes.models import (
    Event,
    MissingHeartbeatDetectionEvent,
    UserGroupAccessLevel
)

import pytest

from conftest import *


@pytest.mark.django_db
def test_missing_heartbeat_detection_event_serialization_deserialization(
        user_factory, task_factory, task_execution_factory,
        api_client) -> None:
    """
    Test that MissingHeartbeatDetectionEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a Task first
    task = task_factory(created_by_group=group)
    task_execution = task_execution_factory(task=task)

    # Create a MissingHeartbeatDetectionEvent manually to avoid factory initialization issues
    from datetime import timedelta
    from django.utils import timezone
    now = timezone.now()
    
    heartbeat_event = MissingHeartbeatDetectionEvent.objects.create(
        created_by_group=group,
        task=task,
        task_execution=task_execution,
        last_heartbeat_at=now - timedelta(minutes=10),
        expected_heartbeat_at=now - timedelta(minutes=5),
        heartbeat_interval_seconds=300,
        severity=Event.Severity.ERROR.value
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test retrieve endpoint
    response = client.get(f'/api/v1/events/{heartbeat_event.uuid}/')
    assert response.status_code == 200
    
    # Verify event_type
    assert response.data['event_type'] == 'missing_heartbeat_detection_event'
    
    # Verify heartbeat-specific fields exist
    assert 'task' in response.data
    assert 'last_heartbeat_at' in response.data
    assert 'expected_heartbeat_at' in response.data
    assert 'heartbeat_interval_seconds' in response.data
    
    # Verify the task reference
    assert response.data['task']['uuid'] == str(task.uuid)
    assert response.data['task']['name'] == task.name
    
    # Verify serialization matches expected format
    ensure_serialized_event_valid(
        response.data,
        heartbeat_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
