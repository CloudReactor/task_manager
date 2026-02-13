from processes.models import (
    Event,
    WorkflowExecution,
    WorkflowExecutionStatusChangeEvent,
    UserGroupAccessLevel
)

import pytest

from conftest import *


@pytest.mark.django_db
def test_workflow_execution_status_change_event_serialization_deserialization(
        user_factory, workflow_factory, workflow_execution_factory,
        workflow_execution_status_change_event_factory,
        api_client) -> None:
    """
    Test that WorkflowExecutionStatusChangeEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a Workflow and WorkflowExecution
    workflow = workflow_factory(created_by_group=group)
    workflow_execution = workflow_execution_factory(workflow=workflow, 
            status=WorkflowExecution.Status.SUCCEEDED)

    # Create a WorkflowExecutionStatusChangeEvent using factory
    status_event = workflow_execution_status_change_event_factory(
        created_by_group=group,
        workflow=workflow,
        workflow_execution=workflow_execution,
        status=WorkflowExecution.Status.SUCCEEDED,
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
    assert response.data['event_type'] == 'workflow_execution_status_change'
    
    # Verify status change-specific fields
    assert 'workflow' in response.data
    assert 'workflow_execution' in response.data
    assert 'status' in response.data
    
    # Verify the workflow and workflow execution references
    assert response.data['workflow']['uuid'] == str(workflow.uuid)
    assert response.data['workflow_execution']['uuid'] == str(workflow_execution.uuid)
    
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
