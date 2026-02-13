import pytest
from django.utils import timezone

from conftest import *
from processes.models import Event, UserGroupAccessLevel


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
