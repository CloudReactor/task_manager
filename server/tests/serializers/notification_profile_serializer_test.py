from typing import cast

import pytest

from processes.common.request_helpers import context_with_request
from processes.models import NotificationProfile
from processes.serializers import NotificationProfileSerializer

from conftest import *


@pytest.mark.django_db
def test_serializer_has_correct_fields(notification_profile_factory,
                                       email_notification_delivery_method_factory,
                                       pager_duty_notification_delivery_method_factory):
    """Test that NotificationProfileSerializer has the expected fields and values."""
    # Create notification delivery methods
    email_ndm = email_notification_delivery_method_factory(
        name='Email Method'
    )
    pagerduty_ndm = pager_duty_notification_delivery_method_factory(
        name='PagerDuty Method',
        created_by_group=email_ndm.created_by_group,
        run_environment=email_ndm.run_environment
    )

    # Create notification profile
    np = cast(NotificationProfile,
              notification_profile_factory(
                  name='Test Notification Profile',
                  description='Test description for profile',
                  enabled=True,
                  created_by_group=email_ndm.created_by_group,
                  run_environment=email_ndm.run_environment
              ))

    # Add notification delivery methods
    np.notification_delivery_methods.add(email_ndm)
    np.notification_delivery_methods.add(pagerduty_ndm)

    context = context_with_request()
    serializer = NotificationProfileSerializer(np, context=context)

    # Get the serialized data
    data = serializer.data

    # Verify field values in the serialized output match expected values
    assert data['uuid'] == str(np.uuid)
    assert data['name'] == 'Test Notification Profile'
    assert data['description'] == 'Test description for profile'
    assert data['enabled'] is True

    # Verify created_by_group is serialized correctly
    assert 'created_by_group' in data
    created_by_group = data['created_by_group']
    assert created_by_group is not None
    assert 'id' in created_by_group
    assert created_by_group['id'] == np.created_by_group.id
    assert 'name' in created_by_group
    assert created_by_group['name'] == np.created_by_group.name

    # Verify run_environment is serialized correctly
    assert 'run_environment' in data
    run_environment = data['run_environment']
    assert run_environment is not None
    assert 'uuid' in run_environment
    assert run_environment['uuid'] == str(np.run_environment.uuid)
    assert 'name' in run_environment
    assert run_environment['name'] == np.run_environment.name
    assert 'url' in run_environment

    # Verify notification_delivery_methods are serialized correctly
    assert 'notification_delivery_methods' in data
    notification_delivery_methods = data['notification_delivery_methods']
    assert isinstance(notification_delivery_methods, list)
    assert len(notification_delivery_methods) == 2

    # Check that both delivery methods are present
    ndm_uuids = [str(email_ndm.uuid), str(pagerduty_ndm.uuid)]
    ndm_names = [email_ndm.name, pagerduty_ndm.name]

    for ndm_data in notification_delivery_methods:
        assert 'uuid' in ndm_data
        assert ndm_data['uuid'] in ndm_uuids
        assert 'name' in ndm_data
        assert ndm_data['name'] in ndm_names
        assert 'url' in ndm_data

    # Verify created_by_user is serialized correctly
    assert 'created_by_user' in data
    assert data['created_by_user'] == np.created_by_user.username

    # Verify other read-only fields are present
    assert 'url' in data
    assert 'created_at' in data
    assert 'updated_at' in data
    assert 'dashboard_url' in data


@pytest.mark.django_db
def test_deserialization(user_factory, run_environment_factory,
                        email_notification_delivery_method_factory):
    """Test that NotificationProfile data can be deserialized correctly."""
    user = user_factory()
    group = user.groups.all()[0]
    run_environment = run_environment_factory(
        created_by_group=group,
        created_by_user=user
    )

    # Create a notification delivery method to reference
    email_ndm = email_notification_delivery_method_factory(
        created_by_group=group,
        run_environment=run_environment
    )

    context = context_with_authenticated_request(
        user=user,
        group=group
    )

    data = {
        'name': 'Test Notification Profile',
        'description': 'Test description',
        'enabled': True,
        'run_environment': {'uuid': str(run_environment.uuid)},
    }

    serializer = NotificationProfileSerializer(data=data, context=context)

    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
    np = serializer.save()

    # Add notification delivery methods after creation
    np.notification_delivery_methods.add(email_ndm)

    # Verify the saved instance
    assert np.name == data['name']
    assert np.description == data['description']
    assert np.enabled is True
    assert np.run_environment.uuid == run_environment.uuid
    assert np.run_environment.name == run_environment.name

    # Verify notification delivery methods
    ndms = np.notification_delivery_methods.all()
    assert ndms.count() == 1
    assert ndms.first().uuid == email_ndm.uuid


@pytest.mark.django_db
def test_deserialization_accepts_notification_delivery_methods_list(
        user_factory, run_environment_factory,
        email_notification_delivery_method_factory,
        pager_duty_notification_delivery_method_factory):
    """Test that NotificationProfileSerializer can create a profile with notification_delivery_methods."""
    user = user_factory()
    group = user.groups.all()[0]
    run_environment = run_environment_factory(
        created_by_group=group,
        created_by_user=user
    )

    # Create notification delivery methods to reference
    email_ndm = email_notification_delivery_method_factory(
        created_by_group=group,
        run_environment=run_environment
    )
    pagerduty_ndm = pager_duty_notification_delivery_method_factory(
        created_by_group=group,
        run_environment=run_environment
    )

    context = context_with_authenticated_request(
        user=user,
        group=group
    )

    data = {
        'name': 'Test Profile With Methods',
        'description': 'Test description',
        'enabled': True,
        'run_environment': {'uuid': str(run_environment.uuid)},
        'notification_delivery_methods': [
            {'uuid': str(email_ndm.uuid)},
            {'uuid': str(pagerduty_ndm.uuid)}
        ]
    }

    serializer = NotificationProfileSerializer(data=data, context=context)

    # Verify the serializer accepts and validates the notification_delivery_methods field
    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"

    # Verify notification_delivery_methods were validated
    assert 'notification_delivery_methods' in serializer.validated_data
    assert len(serializer.validated_data['notification_delivery_methods']) == 2

    # Verify the validated data contains the correct model instances
    validated_uuids = {ndm.uuid for ndm in serializer.validated_data['notification_delivery_methods']}
    expected_uuids = {email_ndm.uuid, pagerduty_ndm.uuid}
    assert validated_uuids == expected_uuids

    # Now save and verify the relationship is persisted
    np = serializer.save()

    # Verify the saved instance
    assert np.name == data['name']
    assert np.description == data['description']
    assert np.enabled is True
    assert np.run_environment.uuid == run_environment.uuid

    # Verify notification delivery methods were set correctly
    ndms = np.notification_delivery_methods.all()
    assert ndms.count() == 2

    ndm_uuids = {ndm.uuid for ndm in ndms}
    assert ndm_uuids == expected_uuids


@pytest.mark.django_db
def test_deserialization_disabled_profile(user_factory, run_environment_factory):
    """Test that a disabled NotificationProfile can be created."""
    user = user_factory()
    group = user.groups.all()[0]
    run_environment = run_environment_factory(
        created_by_group=group,
        created_by_user=user
    )

    context = context_with_authenticated_request(
        user=user,
        group=group
    )

    data = {
        'name': 'Disabled Profile',
        'description': 'This profile is disabled',
        'enabled': False,
        'run_environment': {'uuid': str(run_environment.uuid)},
    }

    serializer = NotificationProfileSerializer(data=data, context=context)

    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
    np = serializer.save()

    # Verify the saved instance
    assert np.name == data['name']
    assert np.enabled is False
    assert np.notification_delivery_methods.count() == 0


@pytest.mark.django_db
def test_update_existing_instance(notification_profile_factory,
                                 email_notification_delivery_method_factory):
    """Test that an existing NotificationProfile can be updated."""
    np = cast(NotificationProfile, notification_profile_factory())

    # Create a new delivery method to add
    new_ndm = email_notification_delivery_method_factory(
        created_by_group=np.created_by_group,
        run_environment=np.run_environment
    )

    context = context_with_authenticated_request(
        user=np.created_by_user,
        group=np.created_by_group
    )

    # Update data
    updated_data = {
        'name': 'Updated Profile Name',
        'description': 'Updated description',
        'enabled': False,
    }

    serializer = NotificationProfileSerializer(
        np, data=updated_data, partial=True, context=context
    )

    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
    updated_np = serializer.save()

    # Update notification delivery methods separately
    updated_np.notification_delivery_methods.clear()
    updated_np.notification_delivery_methods.add(new_ndm)

    # Verify updates
    assert updated_np.name == updated_data['name']
    assert updated_np.description == updated_data['description']
    assert updated_np.enabled is False

    # Verify notification delivery methods were updated
    ndms = updated_np.notification_delivery_methods.all()
    assert ndms.count() == 1
    assert ndms.first().uuid == new_ndm.uuid

    # Verify UUID didn't change
    assert updated_np.uuid == np.uuid


@pytest.mark.django_db
def test_validation_of_notification_delivery_methods_update(
        notification_profile_factory,
        email_notification_delivery_method_factory,
        pager_duty_notification_delivery_method_factory):
    """Test updating an existing NotificationProfile with notification_delivery_methods."""
    # Create initial profile with one delivery method
    initial_ndm = email_notification_delivery_method_factory(name='Initial Email')

    np = cast(NotificationProfile, notification_profile_factory(
        created_by_group=initial_ndm.created_by_group,
        run_environment=initial_ndm.run_environment
    ))
    np.notification_delivery_methods.add(initial_ndm)

    # Create new delivery methods to replace with
    new_email_ndm = email_notification_delivery_method_factory(
        name='New Email',
        created_by_group=np.created_by_group,
        run_environment=np.run_environment
    )
    pagerduty_ndm = pager_duty_notification_delivery_method_factory(
        name='PagerDuty',
        created_by_group=np.created_by_group,
        run_environment=np.run_environment
    )

    context = context_with_authenticated_request(
        user=np.created_by_user,
        group=np.created_by_group
    )

    # Update with new notification delivery methods
    updated_data = {
        'notification_delivery_methods': [
            {'uuid': str(new_email_ndm.uuid)},
            {'uuid': str(pagerduty_ndm.uuid)}
        ]
    }

    serializer = NotificationProfileSerializer(
        np, data=updated_data, partial=True, context=context
    )

    # Verify the serializer validates the notification_delivery_methods field
    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"

    # Verify notification_delivery_methods were validated
    assert 'notification_delivery_methods' in serializer.validated_data
    assert len(serializer.validated_data['notification_delivery_methods']) == 2

    # Verify the validated data contains the correct model instances
    validated_uuids = {ndm.uuid for ndm in serializer.validated_data['notification_delivery_methods']}
    expected_uuids = {new_email_ndm.uuid, pagerduty_ndm.uuid}
    assert validated_uuids == expected_uuids

    # Save and verify the relationship was updated
    updated_np = serializer.save()

    # Verify notification delivery methods were updated correctly
    ndms = updated_np.notification_delivery_methods.all()
    assert ndms.count() == 2

    ndm_uuids = {ndm.uuid for ndm in ndms}
    assert ndm_uuids == expected_uuids

    # Verify initial method was replaced
    assert initial_ndm.uuid not in ndm_uuids


@pytest.mark.django_db
def test_empty_notification_delivery_methods(notification_profile_factory):
    """Test that a NotificationProfile with no delivery methods is serialized correctly."""
    np = cast(NotificationProfile,
              notification_profile_factory(
                  name='Profile Without Methods',
                  enabled=True
              ))

    context = context_with_request()
    serializer = NotificationProfileSerializer(np, context=context)

    data = serializer.data

    # Verify notification_delivery_methods is an empty list
    assert 'notification_delivery_methods' in data
    assert isinstance(data['notification_delivery_methods'], list)
    assert len(data['notification_delivery_methods']) == 0
    assert data['enabled'] is True


@pytest.mark.django_db
def test_multiple_notification_delivery_methods(notification_profile_factory,
                                                email_notification_delivery_method_factory,
                                                pager_duty_notification_delivery_method_factory):
    """Test that a NotificationProfile with multiple delivery methods is serialized correctly."""
    # Create notification delivery methods
    email_ndm1 = email_notification_delivery_method_factory(name='Email 1')
    email_ndm2 = email_notification_delivery_method_factory(
        name='Email 2',
        created_by_group=email_ndm1.created_by_group,
        run_environment=email_ndm1.run_environment
    )
    pagerduty_ndm = pager_duty_notification_delivery_method_factory(
        name='PagerDuty',
        created_by_group=email_ndm1.created_by_group,
        run_environment=email_ndm1.run_environment
    )

    # Create notification profile
    np = cast(NotificationProfile,
              notification_profile_factory(
                  name='Multi-Method Profile',
                  created_by_group=email_ndm1.created_by_group,
                  run_environment=email_ndm1.run_environment
              ))

    # Add all notification delivery methods
    np.notification_delivery_methods.add(email_ndm1)
    np.notification_delivery_methods.add(email_ndm2)
    np.notification_delivery_methods.add(pagerduty_ndm)

    context = context_with_request()
    serializer = NotificationProfileSerializer(np, context=context)

    data = serializer.data

    # Verify all notification_delivery_methods are present
    assert 'notification_delivery_methods' in data
    notification_delivery_methods = data['notification_delivery_methods']
    assert isinstance(notification_delivery_methods, list)
    assert len(notification_delivery_methods) == 3

    # Verify all UUIDs are present
    serialized_uuids = {ndm_data['uuid'] for ndm_data in notification_delivery_methods}
    expected_uuids = {str(email_ndm1.uuid), str(email_ndm2.uuid), str(pagerduty_ndm.uuid)}
    assert serialized_uuids == expected_uuids
