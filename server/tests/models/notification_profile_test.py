from datetime import timezone

from django.utils import timezone

from processes.models import *

from processes.exception.notification_rate_limit_exceeded_exception import (
    NotificationRateLimitExceededException
)

import pytest

@pytest.mark.django_db
def test_send_success(basic_event, group, monkeypatch):

    # Create a notification profile
    profile = NotificationProfile.objects.create(name="Test Profile", created_by_group=group)

    # Create a notification delivery method
    ndm = EmailNotificationDeliveryMethod.objects.create(name="Test NDM",
          created_by_group=group,
          email_to_addresses=["test@example.com"])

    send_result = {'success': True, 'info': 'Email sent successfully'}

    monkeypatch.setattr(EmailNotificationDeliveryMethod, 'send', lambda self, event: send_result,
          raising=False)

    # Associate the NDM with the profile
    profile.notification_delivery_methods.add(ndm)

    # Send a notification
    profile.send(basic_event)

    # Verify that a notification was created
    notifications = profile.notification_set.all()
    assert notifications.count() == 1
    notification = notifications.first()
    assert notification.event == basic_event
    assert notification.notification_delivery_method == ndm
    assert notification.send_status == AlertSendStatus.SUCCEEDED
    assert notification.send_result == send_result
    assert notification.attempted_at is not None
    assert notification.completed_at is not None


@pytest.mark.django_db
def test_send_rate_limited(basic_event, group, monkeypatch):

    # Create a notification profile
    profile = NotificationProfile.objects.create(name="Test Profile", created_by_group=group)

    # Create a notification delivery method
    ndm = EmailNotificationDeliveryMethod.objects.create(name="Test NDM",
          created_by_group=group,
          email_to_addresses=["test@example.com"],
          max_requests_per_period_2=5,
          request_period_seconds_2=60 * 60,
          request_count_in_period_2=5,
          max_severity_2=Event.SEVERITY_WARNING,
          request_period_started_at_2=timezone.now() - timezone.timedelta(minutes=45)
    )

    def rate_limited_send(self, event):
        raise NotificationRateLimitExceededException(event=event, delivery_method=ndm,
                rate_limit_tier_index=2)

    monkeypatch.setattr(EmailNotificationDeliveryMethod, 'send', rate_limited_send,
          raising=False)

    # Associate the NDM with the profile
    profile.notification_delivery_methods.add(ndm)

    # Send a notification
    profile.send(basic_event)

    # Verify that a notification was created
    notifications = profile.notification_set.all()
    assert notifications.count() == 1
    notification = notifications.first()
    assert notification.event == basic_event
    assert notification.notification_delivery_method == ndm
    assert notification.send_status == AlertSendStatus.RATE_LIMITED
    assert notification.send_result is None
    assert notification.rate_limit_tier_index == 2
    assert notification.rate_limit_max_requests_per_period == 5
    assert notification.rate_limit_request_period_seconds == 60 * 60
    assert notification.rate_limit_max_severity == Event.SEVERITY_WARNING
    assert notification.attempted_at is not None
    assert notification.completed_at is None


@pytest.mark.django_db
def test_send_failure(basic_event, group, monkeypatch):

    # Create a notification profile
    profile = NotificationProfile.objects.create(name="Test Profile", created_by_group=group)

    # Create a notification delivery method
    ndm = EmailNotificationDeliveryMethod.objects.create(name="Test NDM",
          created_by_group=group,
          email_to_addresses=["test@example.com"],
    )

    def failing_send(self, event):
        raise RuntimeError("Simulated send failure")

    monkeypatch.setattr(EmailNotificationDeliveryMethod, 'send', failing_send,
          raising=False)

    # Associate the NDM with the profile
    profile.notification_delivery_methods.add(ndm)

    # Send a notification
    profile.send(basic_event)

    # Verify that a notification was created
    notifications = profile.notification_set.all()
    assert notifications.count() == 1
    notification = notifications.first()
    assert notification.event == basic_event
    assert notification.notification_delivery_method == ndm
    assert notification.send_status == AlertSendStatus.FAILED
    assert notification.send_result is None
    assert notification.attempted_at is not None
    assert notification.completed_at is None
    assert notification.exception_type == "RuntimeError"
    assert notification.exception_message == "Simulated send failure"