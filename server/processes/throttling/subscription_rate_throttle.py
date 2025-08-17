from typing import cast

from django.utils import timezone

from rest_framework.throttling import UserRateThrottle

from ..models.group_info import GroupInfo
from ..models.saas_token import SaasToken
from ..models.subscription import Subscription

class SubscriptionRateThrottle(UserRateThrottle):
    # Define a custom scope name to be referenced by DRF in settings.py
    scope = 'subscription'

    def __init__(self):
        super().__init__()
        self.history = []

    def allow_request(self, request, view):
        """
        Override rest_framework.throttling.SimpleRateThrottle.allow_request

        Check to see if the request should be throttled.

        On success calls `throttle_success`.
        On failure calls `throttle_failure`.
        """
        if request.user.is_staff:
            # No throttling
            return True

        if isinstance(request.auth, SaasToken):
            # So superclass has this defined
            self.history = []

            token = cast(SaasToken, request.auth)
            group = token.group
            usage_limits = Subscription.compute_usage_limits(group)
            max_api_credits_per_month = usage_limits.max_api_credits_per_month

            group_info = GroupInfo.objects.filter(group=group).first()

            if not group_info:
                group_info = GroupInfo(group=group)

            now = timezone.now()
            api_last_used_at = group_info.api_last_used_at or now

            current_month = now.month
            current_year = now.year
            last_used_month = api_last_used_at.month
            last_used_year = api_last_used_at.year

            api_credits = 0

            if (last_used_month != current_month) or (last_used_year != current_year):
                if ((last_used_year == current_year) and
                    (last_used_month == current_month - 1)) or (
                    (last_used_year == current_year - 1) and
                    ((last_used_month == 12) and (current_month == 1))):
                    group_info.api_credits_used_previous_month = \
                            group_info.api_credits_used_current_month
            else:
                api_credits = group_info.api_credits_used_current_month

            throttled = False

            if (max_api_credits_per_month is not None) and (api_credits >= max_api_credits_per_month):
                throttled = True
            else:
                group_info.api_credits_used_current_month = api_credits + 1
                group_info.api_last_used_at = now

            group_info.save()

            if throttled:
                return self.throttle_failure()

            return True

        # For users of the website (using JWT), use the default throttle behavior
        return super().allow_request(request, view)
