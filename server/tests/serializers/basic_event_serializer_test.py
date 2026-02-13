from processes.models import (
    Event,
    BasicEvent,
    UserGroupAccessLevel
)

import pytest

from conftest import *


@pytest.mark.django_db
def test_basic_event_serialization_deserialization(
        user_factory,
        basic_event_factory,
        api_client) -> None:
    """
    Test that BasicEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a BasicEvent
    basic_event = basic_event_factory(
        created_by_group=group,
        severity=Event.Severity.INFO.value,
        error_summary="Test basic event summary",
        error_details_message="Test basic event details"
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test retrieve endpoint
    response = client.get(f'/api/v1/events/{basic_event.uuid}/')
    assert response.status_code == 200
    
    # Verify event_type
    assert response.data['event_type'] == 'basic'
    
    # Verify basic fields
    assert response.data['uuid'] == str(basic_event.uuid)
    assert response.data['severity'] == 'info'  # Severity is serialized as lowercase string
    assert response.data['error_summary'] == "Test basic event summary"
    assert response.data['error_details_message'] == "Test basic event details"
    
    # Verify serialization matches expected format
    ensure_serialized_event_valid(
        response.data,
        basic_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )
