"""Tests for NotificationDeliveryMethodViewSet endpoints."""

from unittest.mock import patch

import pytest

from rest_framework.test import APIClient
from rest_framework import status

from processes.models import (
    BasicEvent,
    UserGroupAccessLevel,
    EmailNotificationDeliveryMethod,
)

from conftest import *


@pytest.mark.django_db
def test_test_event_succeeds(
        user_factory, run_environment_factory,
        email_notification_delivery_method_factory):
    """Test that sending a test event succeeds and returns event_uuid."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    method = email_notification_delivery_method_factory(
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    with patch.object(method.__class__, 'send', return_value={'status': 'sent'}):
        response = client.post(
            f'/api/v1/notification_delivery_methods/{method.uuid}/test_event/',
            format='json'
        )

    assert response.status_code == status.HTTP_200_OK
    assert 'event_uuid' in response.data


@pytest.mark.django_db
def test_test_event_creates_basic_event(
        user_factory, run_environment_factory,
        email_notification_delivery_method_factory):
    """Test that a BasicEvent is persisted in the database."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    method = email_notification_delivery_method_factory(
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    before_count = BasicEvent.objects.filter(created_by_group=group).count()

    with patch.object(method.__class__, 'send', return_value=None):
        response = client.post(
            f'/api/v1/notification_delivery_methods/{method.uuid}/test_event/',
            format='json'
        )

    assert response.status_code == status.HTTP_200_OK
    assert BasicEvent.objects.filter(created_by_group=group).count() == before_count + 1

    event = BasicEvent.objects.get(uuid=response.data['event_uuid'])
    assert event.created_by_group == group
    assert event.run_environment == run_environment
    assert 'Test event' in event.error_summary
    assert method.name in event.error_summary


@pytest.mark.django_db
def test_test_event_requires_developer_access(
        user_factory, group_factory, run_environment_factory,
        email_notification_delivery_method_factory):
    """Test that test_event requires at least DEVELOPER access."""
    group = group_factory()

    observer = user_factory()
    observer.groups.add(group)
    UserGroupAccessLevel.objects.filter(user=observer, group=group).delete()
    UserGroupAccessLevel.objects.create(
        user=observer,
        group=group,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER
    )

    admin_user = user_factory()
    admin_user.groups.add(group)
    UserGroupAccessLevel.objects.filter(user=admin_user, group=group).delete()
    UserGroupAccessLevel.objects.create(
        user=admin_user,
        group=group,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN
    )

    run_environment = run_environment_factory(created_by_group=group)
    method = email_notification_delivery_method_factory(
        created_by_group=group,
        created_by_user=admin_user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=observer)

    response = client.post(
        f'/api/v1/notification_delivery_methods/{method.uuid}/test_event/',
        format='json'
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_test_event_unauthenticated_fails(
        user_factory, run_environment_factory,
        email_notification_delivery_method_factory):
    """Test that test_event requires authentication."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    method = email_notification_delivery_method_factory(
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()

    response = client.post(
        f'/api/v1/notification_delivery_methods/{method.uuid}/test_event/',
        format='json'
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_test_event_nonexistent_method(user_factory):
    """Test that test_event returns 404 for a non-existent delivery method."""
    user = user_factory()

    client = APIClient()
    client.force_authenticate(user=user)

    fake_uuid = '00000000-0000-0000-0000-000000000000'
    response = client.post(
        f'/api/v1/notification_delivery_methods/{fake_uuid}/test_event/',
        format='json'
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_test_event_send_failure_returns_502(
        user_factory, run_environment_factory,
        email_notification_delivery_method_factory):
    """Test that a send failure returns 502 Bad Gateway."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    method = email_notification_delivery_method_factory(
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    with patch.object(method.__class__, 'send', side_effect=Exception('SMTP connection failed')):
        response = client.post(
            f'/api/v1/notification_delivery_methods/{method.uuid}/test_event/',
            format='json'
        )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert 'error' in response.data
