from processes.models import (
    Event,
    TaskExecution,
    TaskExecutionStatusChangeEvent,
    UserGroupAccessLevel,
    Execution
)

import pytest

from conftest import *


@pytest.mark.django_db
def test_task_execution_status_change_event_serialization_deserialization(
        user_factory, task_factory, task_execution_factory,
        task_execution_status_change_event_factory,
        api_client) -> None:
    """
    Test that TaskExecutionStatusChangeEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a Task and TaskExecution
    task = task_factory(created_by_group=group)
    task_execution = task_execution_factory(task=task, status=Execution.Status.SUCCEEDED)

    # Create a TaskExecutionStatusChangeEvent using factory
    status_event = task_execution_status_change_event_factory(
        created_by_group=group,
        task=task,
        task_execution=task_execution,
        status=Execution.Status.SUCCEEDED,
        severity=Event.Severity.INFO.value
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test retrieve endpoint
    response = client.get(f'/api/v1/events/{status_event.uuid}/')
    assert response.status_code == 200
    
    # Verify event_type
    assert response.data['event_type'] == 'task_execution_status_change'
    
    # Verify status change-specific fields
    assert 'task' in response.data
    assert 'task_execution' in response.data
    assert 'status' in response.data
    
    # Verify the task and task execution references
    assert response.data['task']['uuid'] == str(task.uuid)
    assert response.data['task_execution']['uuid'] == str(task_execution.uuid)
    
    # Verify status value (serialized as string name)
    assert response.data['status'] == 'SUCCEEDED'
    
    # Verify serialization matches expected format
    ensure_serialized_event_valid(
        response.data,
        status_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
