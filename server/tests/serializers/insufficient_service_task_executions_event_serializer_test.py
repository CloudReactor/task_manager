from processes.models import (
    Event,
    InsufficientServiceTaskExecutionsEvent,
    UserGroupAccessLevel
)

import pytest

from conftest import *


@pytest.mark.django_db
def test_insufficient_service_task_executions_event_serialization_deserialization(
        user_factory, task_factory, run_environment_factory,
        insufficient_service_task_executions_event_factory,
        api_client) -> None:
    """
    Test that InsufficientServiceTaskExecutionsEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a Task and RunEnvironment
    run_environment = run_environment_factory(created_by_group=group)
    task = task_factory(created_by_group=group, run_environment=run_environment)

    # Create an InsufficientServiceTaskExecutionsEvent using factory
    insufficient_event = insufficient_service_task_executions_event_factory(
        created_by_group=group,
        task=task,
        run_environment=run_environment,
        required_concurrency=3,
        detected_concurrency=1,
        severity=Event.Severity.WARNING.value
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test retrieve endpoint
    response = client.get(f'/api/v1/events/{insufficient_event.uuid}/')
    assert response.status_code == 200
    
    # Verify event_type
    assert response.data['event_type'] == 'insufficient_service_task_executions'
    
    # Verify insufficient service-specific fields
    assert 'task' in response.data
    assert 'run_environment' in response.data
    assert 'required_concurrency' in response.data
    assert 'detected_concurrency' in response.data
    
    # Verify the task reference
    assert response.data['task']['uuid'] == str(task.uuid)
    
    # Verify concurrency values
    assert response.data['required_concurrency'] == 3
    assert response.data['detected_concurrency'] == 1
    
    # Verify serialization matches expected format
    ensure_serialized_event_valid(
        response.data,
        insufficient_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
