from typing import cast

import pytest

from processes.common.request_helpers import context_with_request
from processes.models import PagerDutyNotificationDeliveryMethod
from processes.serializers import PagerDutyNotificationDeliveryMethodSerializer

from conftest import *


@pytest.mark.django_db
def test_serializer_has_correct_fields(pager_duty_notification_delivery_method_factory):
    """Test that PagerDutyNotificationDeliveryMethodSerializer has the expected fields and values."""
    pdm = cast(PagerDutyNotificationDeliveryMethod,
               pager_duty_notification_delivery_method_factory(
                   name='Test PagerDuty Method',
                   description='Test description for PagerDuty',
                   pagerduty_api_key='test_key_123',
                   pagerduty_event_class_template='Class: {{ task }}',
                   pagerduty_event_component_template='Component: {{ exec }}',
                   pagerduty_event_group_template='Group: {{ env }}',
                   max_requests_per_period_0=10,
                   request_period_seconds_0=60,
                   max_severity_0=400,
                   max_requests_per_period_1=5,
                   request_period_seconds_1=120,
                   max_severity_1=500,
               ))

    context = context_with_request()
    serializer = PagerDutyNotificationDeliveryMethodSerializer(pdm, context=context)

    # Get the serialized data
    data = serializer.data

    # Verify field values in the serialized output match expected values
    assert data['uuid'] == str(pdm.uuid)
    assert data['name'] == 'Test PagerDuty Method'
    assert data['description'] == 'Test description for PagerDuty'

    # Verify delivery_method_type returns simplified type
    assert data['delivery_method_type'] == 'pager_duty'

    # Verify created_by_group is serialized correctly
    assert 'created_by_group' in data
    created_by_group = data['created_by_group']
    assert created_by_group is not None
    assert 'id' in created_by_group
    assert created_by_group['id'] == pdm.created_by_group.id
    assert 'name' in created_by_group
    assert created_by_group['name'] == pdm.created_by_group.name

    # Verify run_environment is serialized correctly
    assert 'run_environment' in data
    run_environment = data['run_environment']
    assert run_environment is not None
    assert 'uuid' in run_environment
    assert run_environment['uuid'] == str(pdm.run_environment.uuid)
    assert 'name' in run_environment
    assert run_environment['name'] == pdm.run_environment.name
    assert 'url' in run_environment

    assert data['pagerduty_api_key'] == 'test_key_123'
    assert data['pagerduty_event_class_template'] == 'Class: {{ task }}'
    assert data['pagerduty_event_component_template'] == 'Component: {{ exec }}'
    assert data['pagerduty_event_group_template'] == 'Group: {{ env }}'

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
    """Test that PagerDutyNotificationDeliveryMethod data can be deserialized correctly."""
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
        'name': 'Test PagerDuty Method',
        'description': 'Test description',
        'run_environment': { 'uuid': str(run_environment.uuid) },
        'pagerduty_api_key': 'test_api_key_xyz',
        'pagerduty_event_class_template': 'Alert',
        'pagerduty_event_component_template': '{{ task_name }}',
        'pagerduty_event_group_template': '{{ run_environment_name }}',
    }

    serializer = PagerDutyNotificationDeliveryMethodSerializer(data=data, context=context)

    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
    pdm = serializer.save()

    # Verify the saved instance
    assert pdm.name == data['name']
    assert pdm.description == data['description']
    assert pdm.run_environment.uuid == run_environment.uuid
    assert pdm.run_environment.name == run_environment.name
    assert pdm.pagerduty_api_key == data['pagerduty_api_key']
    assert pdm.pagerduty_event_class_template == data['pagerduty_event_class_template']
    assert pdm.pagerduty_event_component_template == data['pagerduty_event_component_template']
    assert pdm.pagerduty_event_group_template == data['pagerduty_event_group_template']


@pytest.mark.django_db
def test_rate_limit_fields(pager_duty_notification_delivery_method_factory):
    """Test that rate limit tier fields are handled correctly."""
    pdm = cast(PagerDutyNotificationDeliveryMethod,
               pager_duty_notification_delivery_method_factory(
                   max_requests_per_period_0=10,
                   request_period_seconds_0=60,
                   max_severity_0=400,
                   max_requests_per_period_1=5,
                   request_period_seconds_1=120,
                   max_severity_1=500,
               ))

    context = context_with_request()
    serializer = PagerDutyNotificationDeliveryMethodSerializer(pdm, context=context)

    # Verify rate limit tiers field is in the serializer
    assert 'rate_limit_tiers' in serializer.fields

    # Verify the model has the rate limit data
    assert pdm.max_requests_per_period_0 == 10
    assert pdm.request_period_seconds_0 == 60
    assert pdm.max_requests_per_period_1 == 5
    assert pdm.request_period_seconds_1 == 120


@pytest.mark.django_db
def test_update_existing_instance(pager_duty_notification_delivery_method_factory):
    """Test that an existing PagerDutyNotificationDeliveryMethod can be updated."""
    pdm = cast(PagerDutyNotificationDeliveryMethod,
               pager_duty_notification_delivery_method_factory())

    context = context_with_authenticated_request(
        user=pdm.created_by_user,
        group=pdm.created_by_group
    )

    # Update data
    updated_data = {
        'name': 'Updated Name',
        'description': 'Updated description',
        'pagerduty_api_key': 'updated_api_key',
        'pagerduty_event_class_template': 'Updated Alert Class',
        'pagerduty_event_component_template': 'Updated {{ task_name }}',
        'pagerduty_event_group_template': 'Updated {{ run_environment_name }}',
    }

    serializer = PagerDutyNotificationDeliveryMethodSerializer(
        pdm, data=updated_data, partial=True, context=context
    )

    assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
    updated_pdm = serializer.save()

    # Verify updates
    assert updated_pdm.name == updated_data['name']
    assert updated_pdm.description == updated_data['description']
    assert updated_pdm.pagerduty_api_key == updated_data['pagerduty_api_key']
    assert updated_pdm.pagerduty_event_class_template == updated_data['pagerduty_event_class_template']
    assert updated_pdm.pagerduty_event_component_template == updated_data['pagerduty_event_component_template']
    assert updated_pdm.pagerduty_event_group_template == updated_data['pagerduty_event_group_template']

    # Verify UUID didn't change
    assert updated_pdm.uuid == pdm.uuid
