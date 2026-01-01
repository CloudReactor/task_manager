from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from processes.models.event import Event
    from processes.models.notification_delivery_method import NotificationDeliveryMethod


class NotificationRateLimitExceededException(Exception):
    """Exception raised when a notification cannot be sent due to rate limiting."""
    def __init__(self, event: Event, delivery_method: NotificationDeliveryMethod,
          rate_limit_tier_index: int = 0):
        super().__init__("Notification rate limit exceeded for delivery method " \
                f"{delivery_method.uuid} {rate_limit_tier_index=} when attempting deliver event " \
                f"{event.uuid} on tier index {rate_limit_tier_index}")
        self.event = event
        self.delivery_method = delivery_method
        self.rate_limit_tier_index = rate_limit_tier_index
