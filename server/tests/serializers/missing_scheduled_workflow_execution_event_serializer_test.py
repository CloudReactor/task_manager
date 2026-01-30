from processes.models import (
    Event,
    MissingScheduledWorkflowExecutionEvent,
    UserGroupAccessLevel
)

import pytest

from conftest import *


@pytest.mark.django_db
def test_missing_scheduled_workflow_execution_event_serialization_deserialization(
        user_factory, workflow_factory,
        api_client) -> None:
    """
    Test that MissingScheduledWorkflowExecutionEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a Workflow first
    workflow = workflow_factory(created_by_group=group)

    # Create a MissingScheduledWorkflowExecutionEvent manually
    from django.utils import timezone
    now = timezone.now()
    
    workflow_event = MissingScheduledWorkflowExecutionEvent.objects.create(
        created_by_group=group,
        workflow=workflow,
        schedule="0 12 * * *",
        expected_execution_at=now,
        severity=Event.Severity.ERROR.value
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test retrieve endpoint
    response = client.get(f'/api/v1/events/{workflow_event.uuid}/')
    assert response.status_code == 200
    
    # Verify event_type
    assert response.data['event_type'] == 'missing_scheduled_workflow_execution_event'
    
    # Verify scheduled workflow execution-specific fields
    assert 'workflow' in response.data
    assert 'schedule' in response.data
    assert 'expected_execution_at' in response.data
    
    # Verify the workflow reference
    assert response.data['workflow']['uuid'] == str(workflow.uuid)
    
    # Verify serialization matches expected format
    ensure_serialized_event_valid(
        response.data,
        workflow_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
