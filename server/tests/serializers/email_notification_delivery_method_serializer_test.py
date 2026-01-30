from typing import cast

import pytest

from processes.common.request_helpers import context_with_request
from processes.models import EmailNotificationDeliveryMethod
from processes.serializers import EmailNotificationDeliveryMethodSerializer

from conftest import *


@pytest.mark.django_db
def test_serializer_has_correct_fields(email_notification_delivery_method_factory):
    """Test that EmailNotificationDeliveryMethodSerializer has the expected fields and values."""
    edm = cast(EmailNotificationDeliveryMethod,
               email_notification_delivery_method_factory(
                   name='Test Email Method',
                   description='Test description for Email',
                   email_to_addresses=['test@example.com', 'user@example.com'],
                   email_cc_addresses=['cc@example.com'],
                   email_bcc_addresses=['bcc@example.com', 'bcc2@example.com'],
                   max_requests_per_period_0=10,
                   request_period_seconds_0=60,
                   max_severity_0=400,
                   max_requests_per_period_1=5,
                   request_period_seconds_1=120,
                   max_severity_1=500,
               ))

    context = context_with_request()
    serializer = EmailNotificationDeliveryMethodSerializer(edm, context=context)

    # Get the serialized data
    data = serializer.data

    # Verify field values in the serialized output match expected values
    assert data['uuid'] == str(edm.uuid)
    assert data['name'] == 'Test Email Method'
    assert data['description'] == 'Test description for Email'

    # Verify delivery_method_type returns simplified type
    assert data['delivery_method_type'] == 'email'

    # Verify created_by_group is serialized correctly
    assert 'created_by_group' in data
    created_by_group = data['created_by_group']
    assert created_by_group is not None
    assert 'id' in created_by_group
    assert created_by_group['id'] == edm.created_by_group.id
    assert 'name' in created_by_group
    assert created_by_group['name'] == edm.created_by_group.name

    # Verify run_environment is serialized correctly
    assert 'run_environment' in data
    run_environment = data['run_environment']
    assert run_environment is not None
    assert 'uuid' in run_environment
    assert run_environment['uuid'] == str(edm.run_environment.uuid)
    assert 'name' in run_environment
    assert run_environment['name'] == edm.run_environment.name
    assert 'url' in run_environment

    # Verify email-specific fields
    assert data['email_to_addresses'] == ['test@example.com', 'user@example.com']
    assert data['email_cc_addresses'] == ['cc@example.com']
    assert data['email_bcc_addresses'] == ['bcc@example.com', 'bcc2@example.com']

    # Verify rate_limit_tiers is present and serialized correctly
    assert 'rate_limit_tiers' in data
    rate_limit_tiers = data['rate_limit_tiers']
    assert isinstance(rate_limit_tiers, list)
    assert len(rate_limit_tiers) == 8  # MAX_RATE_LIMIT_TIERS

    # Verify first tier with data
    tier_0 = rate_limit_tiers[0]
    assert tier_0['max_requests_per_period'] == 10
    assert tier_0['request_period_seconds'] == 60
    assert tier_0['max_severity'] == 'warning'
    assert tier_0['request_period_started_at'] is None
    assert tier_0['request_count_in_period'] is None

    # Verify second tier with data
    tier_1 = rate_limit_tiers[1]
    assert tier_1['max_requests_per_period'] == 5
    assert tier_1['request_period_seconds'] == 120
    assert tier_1['max_severity'] == 'error'
    assert tier_1['request_period_started_at'] is None
    assert tier_1['request_count_in_period'] is None

    # Verify remaining tiers are None
    for i in range(2, 8):
        tier = rate_limit_tiers[i]
        assert tier['max_requests_per_period'] is None
        assert tier['request_period_seconds'] is None
        assert tier['max_severity'] is None
        assert tier['request_period_started_at'] is None
        assert tier['request_count_in_period'] is None


@pytest.mark.django_db
def test_deserialization(user_factory, run_environment_factory):
    """Test that EmailNotificationDeliveryMethod data can be deserialized correctly."""
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
        'name': 'Test Email Method',
        'description': 'Test description',
        'run_environment': { 'uuid': str(run_environment.uuid) },
        'email_to_addresses': ['test@example.com', 'admin@example.com'],
        'email_cc_addresses': ['cc@example.com'],
        'email_bcc_addresses': [],
    }

    serializer = EmailNotificationDeliveryMethodSerializer(data=data, context=context)

    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
    edm = serializer.save()

    # Verify the saved instance
    assert edm.name == data['name']
    assert edm.description == data['description']
    assert edm.run_environment.uuid == run_environment.uuid
    assert edm.run_environment.name == run_environment.name
    assert edm.email_to_addresses == data['email_to_addresses']
    assert edm.email_cc_addresses == data['email_cc_addresses']
    assert edm.email_bcc_addresses == data['email_bcc_addresses']


@pytest.mark.django_db
def test_rate_limit_fields(email_notification_delivery_method_factory):
    """Test that rate limit tier fields are handled correctly."""
    edm = cast(EmailNotificationDeliveryMethod,
               email_notification_delivery_method_factory(
                   max_requests_per_period_0=10,
                   request_period_seconds_0=60,
                   max_severity_0=400,
                   max_requests_per_period_1=5,
                   request_period_seconds_1=120,
                   max_severity_1=500,
               ))

    context = context_with_request()
    serializer = EmailNotificationDeliveryMethodSerializer(edm, context=context)

    # Verify rate limit tiers field is in the serializer
    assert 'rate_limit_tiers' in serializer.fields

    # Verify the model has the rate limit data
    assert edm.max_requests_per_period_0 == 10
    assert edm.request_period_seconds_0 == 60
    assert edm.max_requests_per_period_1 == 5
    assert edm.request_period_seconds_1 == 120


@pytest.mark.django_db
def test_update_existing_instance(email_notification_delivery_method_factory):
    """Test that an existing EmailNotificationDeliveryMethod can be updated."""
    edm = cast(EmailNotificationDeliveryMethod,
               email_notification_delivery_method_factory())

    context = context_with_authenticated_request(
        user=edm.created_by_user,
        group=edm.created_by_group
    )

    # Update data
    updated_data = {
        'name': 'Updated Name',
        'description': 'Updated description',
        'email_to_addresses': ['newemail@example.com'],
        'email_cc_addresses': ['newcc@example.com', 'cc2@example.com'],
        'email_bcc_addresses': ['newbcc@example.com'],
    }

    serializer = EmailNotificationDeliveryMethodSerializer(
        edm, data=updated_data, partial=True, context=context
    )

    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
    updated_edm = serializer.save()

    # Verify updates
    assert updated_edm.name == updated_data['name']
    assert updated_edm.description == updated_data['description']
    assert updated_edm.email_to_addresses == updated_data['email_to_addresses']
    assert updated_edm.email_cc_addresses == updated_data['email_cc_addresses']
    assert updated_edm.email_bcc_addresses == updated_data['email_bcc_addresses']

    # Verify UUID didn't change
    assert updated_edm.uuid == edm.uuid


@pytest.mark.django_db
def test_empty_email_lists(email_notification_delivery_method_factory):
    """Test that empty email address lists are handled correctly."""
    edm = cast(EmailNotificationDeliveryMethod,
               email_notification_delivery_method_factory(
                   name='Test Email Method with minimal addresses',
                   email_to_addresses=['single@example.com'],
                   email_cc_addresses=[],
                   email_bcc_addresses=[],
               ))

    context = context_with_request()
    serializer = EmailNotificationDeliveryMethodSerializer(edm, context=context)

    data = serializer.data

    # Verify email fields
    assert data['email_to_addresses'] == ['single@example.com']
    assert data['email_cc_addresses'] == []
    assert data['email_bcc_addresses'] == []
