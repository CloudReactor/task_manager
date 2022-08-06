from typing import Any, List, Optional, Tuple, cast

from datetime import datetime, timedelta
import uuid

from django.utils import timezone

from django.contrib.auth.models import User, Group

from processes.common.request_helpers import (
  context_with_request
)

from processes.models import (
  GroupInfo, RunEnvironment, UserGroupAccessLevel,
  Subscription, SubscriptionPlan
)

import pytest

from rest_framework.test import APIClient

from conftest import *

MAX_REQUEST_DELAY_SECONDS = 10

@pytest.mark.django_db
@pytest.mark.parametrize("""
  current_usage, api_last_used_days_ago, throttled
""", [
  (None, None, False),
  (999, 0, False),
  (1000, 0, True),
  (1000, 32, False),
])
def test_subscription_rate_throttling(
      current_usage: Optional[int],
      api_last_used_days_ago: Optional[int],
      throttled: bool,
      user_factory, group_info_factory,
      subscription_plan_factory, subscription_factory,
      api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    subscription_plan = subscription_plan_factory(max_api_credits_per_month=1000)
    subscription_factory(subscription_plan=subscription_plan,
            group=group)

    group_info: Optional[GroupInfo] = None
    old_api_last_used_at = None
    if (current_usage is not None) or (api_last_used_days_ago is not None):
        old_api_last_used_at = timezone.now() \
              - timedelta(days=api_last_used_days_ago or 0)
        group_info = group_info_factory(group=group,
                api_credits_used_current_month=current_usage or 0,
                api_last_used_at=old_api_last_used_at)

    old_api_usage = 0

    if group_info:
        old_api_usage = group_info.api_credits_used_current_month

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    params = {
        'created_by_group__id': str(group.id)
    }

    response = client.get('/api/v1/run_environments', params)

    expected_status_code = 429 if throttled else 200

    assert response.status_code == expected_status_code

    if group_info:
        group_info.refresh_from_db()
    else:
        group_info = GroupInfo.objects.get(group=group)

    expected_usage = old_api_usage
    if throttled:
      if old_api_last_used_at is not None:
          assert group_info.api_last_used_at == old_api_last_used_at
    else:
        if (old_api_last_used_at is None) \
                or (group_info.api_last_used_at is None) \
                or ((group_info.api_last_used_at.month == old_api_last_used_at.month) \
                and (group_info.api_last_used_at.year == old_api_last_used_at.year)):
            expected_usage = old_api_usage + 1
        else:
            expected_usage = 1

        assert group_info.api_last_used_at is not None
        assert (timezone.now().timestamp() - group_info.api_last_used_at.timestamp()) < MAX_REQUEST_DELAY_SECONDS

    assert group_info.api_credits_used_current_month == expected_usage
