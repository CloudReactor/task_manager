from typing import Optional

from datetime import timedelta
from django.utils import timezone

from django.contrib.auth.models import Group

from processes.models import (
    Notification,
    Subscription,
)

import pytest

@pytest.mark.django_db
def test_save_notification_exceeding_max_notifications(group: Group, subscription_plan_factory,
        notification_factory):
    utc_now = timezone.now()

    subscription_plan = subscription_plan_factory(max_notifications=3)
    subscription = Subscription(group=group,
          subscription_plan=subscription_plan, active=True,
          start_at=utc_now - timedelta(minutes=1))
    subscription.save()

    earliest_notification: Optional[Notification] = None

    for i in range(5):
        notification = notification_factory(created_by_group=group,
              attempted_at=utc_now - timedelta(minutes=(15 - i)))
        notification.save()

        if earliest_notification is None:
            earliest_notification = notification

    assert Notification.objects.filter(created_by_group=group).count() == 3
    assert Notification.objects.filter(uuid=earliest_notification.uuid).exists() is False