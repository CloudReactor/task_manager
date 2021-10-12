from typing import Optional

import logging

from django.db import models
from django.db.models import Q
from django.utils import timezone

from django.contrib.auth.models import Group

from ..common import UsageLimits
from .subscription_plan import SubscriptionPlan


logger = logging.getLogger(__name__)


class Subscription(models.Model):
    group = models.ForeignKey(Group, null=True, on_delete=models.SET_NULL)
    subscription_plan = models.ForeignKey(SubscriptionPlan, null=True,
            on_delete=models.SET_NULL)
    active = models.BooleanField(default=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_at = models.DateTimeField(null=False)
    end_at = models.DateTimeField(null=True, blank=True)


    @staticmethod
    def compute_usage_limits(group: Group) -> UsageLimits:
        utc_now = timezone.now()
        subscriptions = Subscription.objects.select_related('subscription_plan') \
                .filter(Q(group=group), Q(active=True), Q(start_at__lte=utc_now),
                Q(end_at__gte=utc_now) | Q(end_at__isnull=True)).all()

        usage_limits: Optional[UsageLimits] = None

        for subscription in subscriptions:
            plan = subscription.subscription_plan
            if plan:
                sul = plan.usage_limits
                if usage_limits:
                    usage_limits = usage_limits.combine(sul)
                else:
                    usage_limits = sul

        if usage_limits:
            return usage_limits
        else:
            logger.debug(f'No subscription found for {group=}, returning default limits')
            return UsageLimits.default_limits()

    def __str__(self):
        if self.group and self.subscription_plan:
            return self.group.name + '/' + self.subscription_plan.name + '/'+ str(self.pk)

        return str(self.pk)
