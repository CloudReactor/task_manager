"""Tests for cloning functionality in viewsets."""

from typing import Any

import pytest

from django.contrib.auth.models import User

from rest_framework.test import APIClient
from rest_framework import status

from processes.models import (
    NotificationProfile, NotificationDeliveryMethod, RunEnvironment,
    UserGroupAccessLevel, EmailNotificationDeliveryMethod, SaasToken
)
from processes.serializers import (
    NotificationProfileSerializer, NotificationDeliveryMethodSerializer
)

from conftest import context_with_authenticated_request, make_saas_token_api_client


@pytest.mark.django_db
def test_clone_notification_profile_with_custom_name(
        user_factory, run_environment_factory,
        notification_profile_factory):
    """Test cloning a notification profile with a custom name."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    profile = notification_profile_factory(
        name='Original Profile',
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f'/api/v1/notification_profiles/{profile.uuid}/clone/',
        data={'name': 'Custom Cloned Profile'},
        format='json'
    )

    assert response.status_code == status.HTTP_201_CREATED
    cloned = NotificationProfile.objects.get(uuid=response.data['uuid'])

    # Verify clone has new name and UUID
    assert cloned.name == 'Custom Cloned Profile'
    assert cloned.uuid != profile.uuid

    # Verify same group/user
    assert cloned.created_by_group == profile.created_by_group
    assert cloned.created_by_user == profile.created_by_user
    assert cloned.run_environment == profile.run_environment


@pytest.mark.django_db
def test_clone_notification_profile_with_auto_generated_name(
        user_factory, run_environment_factory,
        notification_profile_factory):
    """Test cloning with auto-generated name when none provided."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    profile = notification_profile_factory(
        name='Original',
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f'/api/v1/notification_profiles/{profile.uuid}/clone/',
        data={},
        format='json'
    )

    assert response.status_code == status.HTTP_201_CREATED
    cloned = NotificationProfile.objects.get(uuid=response.data['uuid'])

    # Name should be auto-generated with "copy" suffix
    assert 'Original' in cloned.name
    assert cloned.name != profile.name


@pytest.mark.django_db
def test_clone_notification_delivery_method(
        user_factory, run_environment_factory,
        email_notification_delivery_method_factory):
    """Test cloning an email notification delivery method."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    method = email_notification_delivery_method_factory(
        name='Original Email Method',
        email_to_addresses=['test@example.com'],
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f'/api/v1/notification_delivery_methods/{method.uuid}/clone/',
        data={'name': 'Cloned Email Method'},
        format='json'
    )

    assert response.status_code == status.HTTP_201_CREATED
    cloned = EmailNotificationDeliveryMethod.objects.get(uuid=response.data['uuid'])

    # Verify clone
    assert cloned.name == 'Cloned Email Method'
    assert cloned.uuid != method.uuid
    assert cloned.email_to_addresses == method.email_to_addresses
    assert cloned.created_by_group == method.created_by_group


@pytest.mark.django_db
def test_clone_requires_developer_access(
        user_factory, group_factory, run_environment_factory,
        notification_profile_factory):
    """Test that cloning requires at least DEVELOPER access."""
    group = group_factory()
    # User with OBSERVER access
    user = user_factory()
    user.groups.add(group)
    UserGroupAccessLevel.objects.filter(user=user, group=group).delete()
    UserGroupAccessLevel.objects.create(
        user=user,
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

    profile = notification_profile_factory(
        name='Original Profile',
        created_by_group=group,
        created_by_user=admin_user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f'/api/v1/notification_profiles/{profile.uuid}/clone/',
        data={'name': 'Cloned Profile'},
        format='json'
    )

    # Should fail with 403 Forbidden
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_clone_with_developer_access_succeeds(
        user_factory, group_factory, run_environment_factory,
        notification_profile_factory):
    """Test that cloning succeeds with DEVELOPER access."""
    group = group_factory()
    # User with DEVELOPER access
    user = user_factory()
    user.groups.add(group)
    UserGroupAccessLevel.objects.filter(user=user, group=group).delete()
    UserGroupAccessLevel.objects.create(
        user=user,
        group=group,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
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

    profile = notification_profile_factory(
        name='Original Profile',
        created_by_group=group,
        created_by_user=admin_user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f'/api/v1/notification_profiles/{profile.uuid}/clone/',
        data={'name': 'Cloned Profile'},
        format='json'
    )

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_clone_unauthenticated_fails(
        user_factory, run_environment_factory,
        notification_profile_factory):
    """Test that cloning without authentication fails."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    profile = notification_profile_factory(
        name='Original Profile',
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()

    response = client.post(
        f'/api/v1/notification_profiles/{profile.uuid}/clone/',
        data={'name': 'Cloned Profile'},
        format='json'
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_clone_different_group_fails(
        user_factory, group_factory, run_environment_factory,
        notification_profile_factory):
    """Test that cloning from a different group fails."""
    group1 = group_factory()
    group2 = group_factory()

    # User with DEVELOPER access in group2
    user = user_factory()
    user.groups.add(group2)
    UserGroupAccessLevel.objects.filter(user=user, group=group2).delete()
    UserGroupAccessLevel.objects.create(
        user=user,
        group=group2,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )

    admin_user = user_factory()
    admin_user.groups.add(group1)
    UserGroupAccessLevel.objects.filter(user=admin_user, group=group1).delete()
    UserGroupAccessLevel.objects.create(
        user=admin_user,
        group=group1,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN
    )

    run_environment = run_environment_factory(created_by_group=group1)

    # Profile created by group1
    profile = notification_profile_factory(
        name='Original Profile',
        created_by_group=group1,
        created_by_user=admin_user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f'/api/v1/notification_profiles/{profile.uuid}/clone/',
        data={'name': 'Cloned Profile'},
        format='json'
    )

    # Should fail - user from different group
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_clone_preserves_all_fields(
        user_factory, run_environment_factory,
        email_notification_delivery_method_factory):
    """Test that cloning preserves all relevant fields."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    original = email_notification_delivery_method_factory(
        name='Original',
        email_to_addresses=['to@example.com'],
        email_cc_addresses=['cc@example.com'],
        email_bcc_addresses=['bcc@example.com'],
        enabled=True,
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f'/api/v1/notification_delivery_methods/{original.uuid}/clone/',
        data={'name': 'Cloned'},
        format='json'
    )

    assert response.status_code == status.HTTP_201_CREATED
    cloned = EmailNotificationDeliveryMethod.objects.get(uuid=response.data['uuid'])

    # Verify all fields preserved
    assert cloned.email_to_addresses == original.email_to_addresses
    assert cloned.email_cc_addresses == original.email_cc_addresses
    assert cloned.email_bcc_addresses == original.email_bcc_addresses
    assert cloned.enabled == original.enabled
    assert cloned.type == original.type


@pytest.mark.django_db
def test_clone_resets_timestamps(
        user_factory, run_environment_factory,
        notification_profile_factory):
    """Test that cloning resets created_at and updated_at."""
    import time
    from django.utils import timezone

    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    original = notification_profile_factory(
        name='Original',
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    original_created_at = original.created_at
    original_updated_at = original.updated_at

    # Wait a bit to ensure timestamp difference
    time.sleep(0.1)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f'/api/v1/notification_profiles/{original.uuid}/clone/',
        data={'name': 'Cloned'},
        format='json'
    )

    assert response.status_code == status.HTTP_201_CREATED
    cloned = NotificationProfile.objects.get(uuid=response.data['uuid'])

    # Timestamps should be newer
    assert cloned.created_at > original_created_at
    assert cloned.updated_at > original_updated_at


@pytest.mark.django_db
def test_clone_multiple_times(
        user_factory, run_environment_factory,
        notification_profile_factory):
    """Test cloning the same profile multiple times produces different UUIDs."""
    user = user_factory()
    group = user.groups.first()
    run_environment = run_environment_factory(created_by_group=group)

    original = notification_profile_factory(
        name='Original',
        created_by_group=group,
        created_by_user=user,
        run_environment=run_environment
    )

    client = APIClient()
    client.force_authenticate(user=user)

    # Clone 3 times
    responses = []
    for i in range(3):
        response = client.post(
            f'/api/v1/notification_profiles/{original.uuid}/clone/',
            data={'name': f'Clone {i+1}'},
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        responses.append(response)

    # All UUIDs should be different
    uuids = [r.data['uuid'] for r in responses]
    assert len(set(uuids)) == 3  # All unique


@pytest.mark.django_db
def test_clone_with_api_key_scoped_to_different_run_environment(
        user_factory, group_factory, run_environment_factory,
        notification_profile_factory):
    """Test that cloning fails when API key is scoped to a different Run Environment."""
    from processes.models import SaasToken, UserGroupAccessLevel
    from conftest import make_saas_token_api_client

    group = group_factory()
    admin_user = user_factory()
    admin_user.groups.add(group)
    UserGroupAccessLevel.objects.filter(user=admin_user, group=group).delete()
    UserGroupAccessLevel.objects.create(
        user=admin_user,
        group=group,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN
    )

    # Create two different run environments
    run_environment_1 = run_environment_factory(created_by_group=group)
    run_environment_2 = run_environment_factory(created_by_group=group)

    # Create a profile with run_environment_1
    profile = notification_profile_factory(
        name='Original Profile',
        created_by_group=group,
        created_by_user=admin_user,
        run_environment=run_environment_1
    )

    # Create an API key scoped to run_environment_2
    api_key_user = user_factory()
    api_key_user.groups.add(group)
    UserGroupAccessLevel.objects.filter(user=api_key_user, group=group).delete()
    UserGroupAccessLevel.objects.create(
        user=api_key_user,
        group=group,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )

    client = APIClient()
    client = make_saas_token_api_client(
        user=api_key_user,
        group=group,
        api_client=client,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        run_environment=run_environment_2
    )

    response = client.post(
        f'/api/v1/notification_profiles/{profile.uuid}/clone/',
        data={'name': 'Cloned Profile'},
        format='json'
    )

    # Should fail with 403 - API key doesn't have access to profile's run environment
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_clone_nonexistent_profile(user_factory):
    """Test cloning a profile that doesn't exist."""
    user = user_factory()

    client = APIClient()
    client.force_authenticate(user=user)

    fake_uuid = '00000000-0000-0000-0000-000000000000'

    response = client.post(
        f'/api/v1/notification_profiles/{fake_uuid}/clone/',
        data={'name': 'Cloned'},
        format='json'
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
