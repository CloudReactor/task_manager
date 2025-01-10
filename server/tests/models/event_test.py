from typing import Optional

from datetime import timedelta
from django.utils import timezone

from django.contrib.auth.models import Group

from processes.models import (
    Event,
    Subscription,
)

import pytest

@pytest.mark.django_db
def test_save_event_exceeding_max_events(group: Group, subscription_plan_factory,
        basic_event_factory):
    utc_now = timezone.now()

    subscription_plan = subscription_plan_factory(max_events=3)
    subscription = Subscription(group=group,
          subscription_plan=subscription_plan, active=True,
          start_at=utc_now - timedelta(minutes=1))
    subscription.save()

    earliest_event: Optional[Event] = None

    for i in range(5):
        event = basic_event_factory(created_by_group=group,
              event_at=utc_now - timedelta(minutes=(15 - i)))
        event.save()

        if earliest_event is None:
            earliest_event = event

    assert Event.objects.filter(created_by_group=group).count() == 3
    assert Event.objects.filter(uuid=earliest_event.uuid).exists() is False