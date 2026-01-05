from typing import cast

import pytest

from processes.common.request_helpers import context_with_request
from processes.models import PagerDutyNotificationDeliveryMethod
from processes.serializers import PagerDutyNotificationDeliveryMethodSerializer

from conftest import *


@pytest.mark.django_db
def test_serializer_has_correct_fields(pager_duty_notification_delivery_method_factory):
    """Test that PagerDutyNotificationDeliveryMethodSerializer has the expected fields."""
    pdm = cast(PagerDutyNotificationDeliveryMethod,
               pager_duty_notification_delivery_method_factory())

    context = context_with_request()
    serializer = PagerDutyNotificationDeliveryMethodSerializer(pdm, context=context)

    # Verify the serializer has the expected fields
    fields = serializer.fields.keys()

    # Verify basic fields are present
    assert 'name' in fields
    assert 'description' in fields
    assert 'uuid' in fields
    assert 'run_environment' in fields

    # Verify PagerDuty-specific fields are present
    assert 'pagerduty_api_key' in fields
    assert 'pagerduty_event_class_template' in fields
    assert 'pagerduty_event_component_template' in fields
    assert 'pagerduty_event_group_template' in fields

    # Verify rate_limit_tiers field is present
    assert 'rate_limit_tiers' in fields


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
