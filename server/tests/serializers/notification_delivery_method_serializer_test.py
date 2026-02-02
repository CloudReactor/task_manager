from typing import cast
from datetime import datetime, timedelta, timezone

import pytest

from processes.common.request_helpers import context_with_request
from processes.models import (
    NotificationDeliveryMethod,
    EmailNotificationDeliveryMethod,    
)
from processes.serializers import NotificationDeliveryMethodSerializer

from conftest import *


@pytest.mark.django_db
def test_serializer_has_correct_fields(email_notification_delivery_method_factory):
    """Test that NotificationDeliveryMethodSerializer has the expected fields and values."""
    ndm = email_notification_delivery_method_factory(
        name='Test Notification Method',
        description='Test description',
        max_requests_per_period_0=10,
        request_period_seconds_0=60,
        max_severity_0=400,
        max_requests_per_period_1=50,
        request_period_seconds_1=3600,
        max_severity_1=None,
        request_count_in_period_0=5,
        request_count_in_period_1=0,
    )

    context = context_with_request()
    serializer = NotificationDeliveryMethodSerializer(ndm, context=context)

    data = serializer.data

    assert data['uuid'] == str(ndm.uuid)
    assert data['name'] == 'Test Notification Method'
    assert data['description'] == 'Test description'
    assert 'url' in data
    assert 'created_by_group' in data
    assert 'created_at' in data
    assert 'updated_at' in data


@pytest.mark.django_db
def test_rate_limit_tiers_serialization(email_notification_delivery_method_factory):
    """Test that rate limit tiers are correctly serialized."""
    now = datetime.now(timezone.utc)
    ndm = email_notification_delivery_method_factory(
        max_requests_per_period_0=10,
        request_period_seconds_0=60,
        max_severity_0=400,
        request_period_started_at_0=now - timedelta(minutes=5),
        request_count_in_period_0=3,
        max_requests_per_period_1=50,
        request_period_seconds_1=3600,
        max_severity_1=500,
        request_period_started_at_1=now - timedelta(hours=1),
        request_count_in_period_1=25,
    )

    context = context_with_request()
    serializer = NotificationDeliveryMethodSerializer(ndm, context=context)
    data = serializer.data

    # Verify rate_limit_tiers exists and is a list
    assert 'rate_limit_tiers' in data
    assert isinstance(data['rate_limit_tiers'], list)

    # Verify tier 0
    tier0 = data['rate_limit_tiers'][0]
    assert tier0['max_requests_per_period'] == 10
    assert tier0['request_period_seconds'] == 60
    assert tier0['max_severity'] == 'warning'
    assert tier0['request_count_in_period'] == 3
    assert tier0['request_period_started_at'] is not None

    # Verify tier 1
    tier1 = data['rate_limit_tiers'][1]
    assert tier1['max_requests_per_period'] == 50
    assert tier1['request_period_seconds'] == 3600
    assert tier1['max_severity'] == 'error'
    assert tier1['request_count_in_period'] == 25
    assert tier1['request_period_started_at'] is not None


@pytest.mark.django_db
def test_rate_limit_tiers_with_null_values(email_notification_delivery_method_factory):
    """Test that rate limit tiers handle null values correctly."""
    ndm = email_notification_delivery_method_factory(
        max_requests_per_period_0=10,
        request_period_seconds_0=60,
        max_severity_0=None,
        request_period_started_at_0=None,
        request_count_in_period_0=None,
        max_requests_per_period_1=None,
        request_period_seconds_1=None,
        max_severity_1=None,
        request_period_started_at_1=None,
        request_count_in_period_1=None,
    )

    context = context_with_request()
    serializer = NotificationDeliveryMethodSerializer(ndm, context=context)
    data = serializer.data

    rate_limit_tiers = data['rate_limit_tiers']
    
    # Verify tier 0 with null severity
    tier0 = rate_limit_tiers[0]
    assert tier0['max_requests_per_period'] == 10
    assert tier0['request_period_seconds'] == 60
    assert tier0['max_severity'] is None
    assert tier0['request_period_started_at'] is None
    assert tier0['request_count_in_period'] is None

    # Verify tier 1 with all nulls
    tier1 = rate_limit_tiers[1]
    assert tier1['max_requests_per_period'] is None
    assert tier1['request_period_seconds'] is None
    assert tier1['max_severity'] is None
    assert tier1['request_period_started_at'] is None
    assert tier1['request_count_in_period'] is None


@pytest.mark.django_db
def test_delivery_method_type_serialization_for_email(email_notification_delivery_method_factory):
    """Test that delivery_method_type returns 'email' for EmailNotificationDeliveryMethod."""
    edm = cast(EmailNotificationDeliveryMethod, email_notification_delivery_method_factory(
        email_to_addresses=['test@example.com'],
        max_requests_per_period_0=10,
        request_period_seconds_0=60,
    ))

    context = context_with_request()
    serializer = NotificationDeliveryMethodSerializer(edm, context=context)
    data = serializer.data

    assert data['delivery_method_type'] == 'email'


@pytest.mark.django_db
def test_enabled_field(email_notification_delivery_method_factory):
    """Test that the enabled field is correctly serialized."""
    ndm_enabled = email_notification_delivery_method_factory(
        enabled=True,
        max_requests_per_period_0=10,
        request_period_seconds_0=60,
    )

    ndm_disabled = email_notification_delivery_method_factory(
        enabled=False,
        max_requests_per_period_0=10,
        request_period_seconds_0=60,
    )

    context = context_with_request()

    serializer_enabled = NotificationDeliveryMethodSerializer(ndm_enabled, context=context)
    assert serializer_enabled.data['enabled'] is True

    serializer_disabled = NotificationDeliveryMethodSerializer(ndm_disabled, context=context)
    assert serializer_disabled.data['enabled'] is False


@pytest.mark.django_db
def test_to_internal_value_with_rate_limit_tiers(user_factory):
    """Test that to_internal_value correctly processes rate_limit_tiers from input data."""
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)
    
    data = {
        'name': 'Test Method',
        'description': 'Test',
        'enabled': True,
        'delivery_method_type': 'email',
        'rate_limit_tiers': [
            {
                'max_requests_per_period': 10,
                'request_period_seconds': 60,
                'max_severity': 'warning',
                'request_period_started_at': None,
                'request_count_in_period': 0,
            },
            {
                'max_requests_per_period': 50,
                'request_period_seconds': 3600,
                'max_severity': 'error',
                'request_period_started_at': None,
                'request_count_in_period': 0,
            },
        ] + [
            {
                'max_requests_per_period': None,
                'request_period_seconds': None,
                'max_severity': None,
                'request_period_started_at': None,
                'request_count_in_period': None,
            }
            for _ in range(NotificationDeliveryMethod.MAX_RATE_LIMIT_TIERS - 2)
        ]
    }

    context = context_with_authenticated_request(user=user, group=group)
    
    serializer = NotificationDeliveryMethodSerializer(data=data, context=context)
    
    # Verify the serializer is valid
    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"

    # Verify the internal value contains the rate limit tier fields
    internal_value = serializer.validated_data
    assert internal_value['max_requests_per_period_0'] == 10
    assert internal_value['request_period_seconds_0'] == 60
    assert internal_value['max_severity_0'] == 400  # 'warning' converted to numeric
    assert internal_value['request_count_in_period_0'] == 0

    assert internal_value['max_requests_per_period_1'] == 50
    assert internal_value['request_period_seconds_1'] == 3600
    assert internal_value['max_severity_1'] == 500  # 'error' converted to numeric
    assert internal_value['request_count_in_period_1'] == 0


@pytest.mark.django_db
def test_readonly_fields(user_factory, email_notification_delivery_method_factory):
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)
    
    """Test that readonly fields cannot be modified during update."""
    ndm = email_notification_delivery_method_factory(
        name='Original Name',
        max_requests_per_period_0=10,
        request_period_seconds_0=60,
        created_by_user=user,
        created_by_group=group
    )

    data = {
        'name': 'Updated Name',
        'created_at': '2020-01-01T00:00:00Z',
        'updated_at': '2020-01-01T00:00:00Z',
    }

    context = context_with_authenticated_request(user=user, group=group)
    serializer = NotificationDeliveryMethodSerializer(ndm, data=data, partial=True, context=context)

    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"

    # Verify that only the name was updated, not the readonly fields
    assert serializer.validated_data['name'] == 'Updated Name'
    assert 'created_at' not in serializer.validated_data
    assert 'updated_at' not in serializer.validated_data


@pytest.mark.django_db
def test_all_max_rate_limit_tiers_present(email_notification_delivery_method_factory):
    """Test that all MAX_RATE_LIMIT_TIERS are present in the serialized output."""
    ndm = email_notification_delivery_method_factory(
        max_requests_per_period_0=10,
        request_period_seconds_0=60,
    )

    context = context_with_request()
    serializer = NotificationDeliveryMethodSerializer(ndm, context=context)
    data = serializer.data

    rate_limit_tiers = data['rate_limit_tiers']
    assert len(rate_limit_tiers) == NotificationDeliveryMethod.MAX_RATE_LIMIT_TIERS


@pytest.mark.django_db
def test_run_environment_serialization(email_notification_delivery_method_factory, run_environment_factory):
    """Test that run_environment is correctly serialized."""
    run_env = run_environment_factory()
    ndm = email_notification_delivery_method_factory(
        run_environment=run_env,
        max_requests_per_period_0=10,
        request_period_seconds_0=60,
    )

    context = context_with_request()
    serializer = NotificationDeliveryMethodSerializer(ndm, context=context)
    data = serializer.data

    assert 'run_environment' in data
    
    assert 'uuid' in data['run_environment']
    assert data['run_environment']['uuid'] == str(run_env.uuid)
    assert data['run_environment']['name'] == run_env.name
