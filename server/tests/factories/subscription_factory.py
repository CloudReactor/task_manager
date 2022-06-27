from datetime import timedelta

from django.utils import timezone

from processes.models import Subscription

import factory

from pytest_factoryboy import register

from .group_factory import GroupFactory
from .subscription_plan_factory import SubscriptionPlanFactory


@register
class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    group = factory.SubFactory(GroupFactory)
    subscription_plan = factory.SubFactory(SubscriptionPlanFactory)
    active = True
    created_at = timezone.now()
    updated_at = timezone.now()
    start_at = timezone.now() - timedelta(days=30)
    end_at = None
