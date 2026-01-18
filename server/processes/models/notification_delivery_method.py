from __future__ import annotations

import logging

from typing import Any

from abc import abstractmethod

from django.db import models
from django.utils import timezone

from typedmodels.models import TypedModel

from ..exception.notification_rate_limit_exceeded_exception import \
    NotificationRateLimitExceededException

from .event import Event
from .named_with_uuid_and_run_environment_model import NamedWithUuidAndRunEnvironmentModel

logger = logging.getLogger(__name__)


class NotificationDeliveryMethod(TypedModel, NamedWithUuidAndRunEnvironmentModel):
    MAX_RATE_LIMIT_TIERS = 8

    enabled = models.BooleanField(default=True)

    max_requests_per_period_0 = models.PositiveIntegerField(null=True, blank=True, default=5)
    request_period_seconds_0 = models.PositiveIntegerField(null=True, blank=True, default=60)
    max_severity_0 = models.PositiveIntegerField(null=True, blank=True)
    request_period_started_at_0 = models.DateTimeField(null=True, blank=True)
    request_count_in_period_0 = models.PositiveIntegerField(null=True, blank=True)

    max_requests_per_period_1 = models.PositiveIntegerField(null=True, blank=True, default=30)
    request_period_seconds_1 = models.PositiveIntegerField(null=True, blank=True, default=60 * 60)
    max_severity_1 = models.PositiveIntegerField(null=True, blank=True)
    request_period_started_at_1 = models.DateTimeField(null=True, blank=True)
    request_count_in_period_1 = models.PositiveIntegerField(null=True, blank=True)

    max_requests_per_period_2 = models.PositiveIntegerField(null=True, blank=True, default=100)
    request_period_seconds_2 = models.PositiveIntegerField(null=True, blank=True, default=24 * 60 * 60)
    max_severity_2 = models.PositiveIntegerField(null=True, blank=True)
    request_period_started_at_2 = models.DateTimeField(null=True, blank=True)
    request_count_in_period_2 = models.PositiveIntegerField(null=True, blank=True)

    max_requests_per_period_3 = models.PositiveIntegerField(null=True, blank=True)
    request_period_seconds_3 = models.PositiveIntegerField(null=True, blank=True)
    max_severity_3 = models.PositiveIntegerField(null=True, blank=True)
    request_period_started_at_3 = models.DateTimeField(null=True, blank=True)
    request_count_in_period_3 = models.PositiveIntegerField(null=True, blank=True)

    max_requests_per_period_4 = models.PositiveIntegerField(null=True, blank=True)
    request_period_seconds_4 = models.PositiveIntegerField(null=True, blank=True)
    max_severity_4 = models.PositiveIntegerField(null=True, blank=True)
    request_period_started_at_4 = models.DateTimeField(null=True, blank=True)
    request_count_in_period_4 = models.PositiveIntegerField(null=True, blank=True)

    max_requests_per_period_5 = models.PositiveIntegerField(null=True, blank=True)
    request_period_seconds_5 = models.PositiveIntegerField(null=True, blank=True)
    max_severity_5 = models.PositiveIntegerField(null=True, blank=True)
    request_period_started_at_5 = models.DateTimeField(null=True, blank=True)
    request_count_in_period_5 = models.PositiveIntegerField(null=True, blank=True)

    max_requests_per_period_6 = models.PositiveIntegerField(null=True, blank=True)
    request_period_seconds_6 = models.PositiveIntegerField(null=True, blank=True)
    max_severity_6 = models.PositiveIntegerField(null=True, blank=True)
    request_period_started_at_6 = models.DateTimeField(null=True, blank=True)
    request_count_in_period_6 = models.PositiveIntegerField(null=True, blank=True)

    max_requests_per_period_7 = models.PositiveIntegerField(null=True, blank=True)
    request_period_seconds_7 = models.PositiveIntegerField(null=True, blank=True)
    max_severity_7 = models.PositiveIntegerField(null=True, blank=True)
    request_period_started_at_7 = models.DateTimeField(null=True, blank=True)
    request_count_in_period_7 = models.PositiveIntegerField(null=True, blank=True)


    def send_if_not_rate_limited(self, event: Event) -> dict[str, Any] | None:
        if self.enabled is False:
            logger.info(f"Skipping Notification Delivery Method {self.uuid} / {self.name} because it is disabled")
            return None

        tier_index = self.rate_limited_tier_index(event)

        if tier_index is not None:
            raise NotificationRateLimitExceededException(event=event, delivery_method=self,
                    rate_limit_tier_index=tier_index)

        result = self.send(event)

        self.increment_rate_limit_counters(event)

        return result

    def will_be_rate_limited(self, event: Event) -> bool:
        return self.rate_limited_tier_index(event) is not None

    def rate_limited_tier_index(self, event: Event) -> int | None:
        now = timezone.now()

        for tier_index in range(self.MAX_RATE_LIMIT_TIERS):
            max_requests = getattr(self, f'max_requests_per_period_{tier_index}')
            period_seconds = getattr(self, f'request_period_seconds_{tier_index}')
            max_severity = getattr(self, f'max_severity_{tier_index}')

            if max_requests is None or period_seconds is None:
                continue

            if max_severity is not None and event.severity > max_severity:
                continue

            request_count_in_period = getattr(self, f'request_count_in_period_{tier_index}') or 0

            period_started_at = getattr(self, f'request_period_started_at_{tier_index}')

            if period_started_at is None or (now - period_started_at).total_seconds() > period_seconds:
                logger.debug(f"Previous rate limit period expired for delivery method {self.uuid} tier {tier_index}")
                request_count_in_period = 0

            if request_count_in_period >= max_requests:
                logger.info(f"Notification delivery method {self.uuid} rate limited on tier {tier_index}")
                return tier_index

        return None

    def increment_rate_limit_counters(self, event: Event) -> None:
        now = timezone.now()

        update_fields: list[str] = []

        for tier_index in range(self.MAX_RATE_LIMIT_TIERS):
            max_requests = getattr(self, f'max_requests_per_period_{tier_index}')
            period_seconds = getattr(self, f'request_period_seconds_{tier_index}')
            max_severity = getattr(self, f'max_severity_{tier_index}')

            if max_requests is None or period_seconds is None:
                continue

            if max_severity is not None and event.severity > max_severity:
                continue

            request_count_attr = f'request_count_in_period_{tier_index}'

            update_fields.append(request_count_attr)

            request_count_in_period = getattr(self, request_count_attr) or 0

            period_started_at_attr = f'request_period_started_at_{tier_index}'

            period_started_at = getattr(self, period_started_at_attr)

            if period_started_at is None or (now - period_started_at).total_seconds() > period_seconds:
                logger.debug(f"Rate limit period reset for delivery method {self.uuid} tier {tier_index}")
                request_count_in_period = 0
                setattr(self, period_started_at_attr, now)
                update_fields.append(period_started_at_attr)

            setattr(self, request_count_attr, request_count_in_period + 1)

        self.save(update_fields=update_fields)

    @abstractmethod
    def send(self, event: Event) -> dict[str, Any] | None:
        raise NotImplementedError()
