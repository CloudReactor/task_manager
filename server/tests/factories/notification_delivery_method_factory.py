import factory

from processes.models import NotificationDeliveryMethod

from .owned_model_factory import OwnedModelFactory


class NotificationDeliveryMethodFactory(OwnedModelFactory):
    class Meta:
        model = NotificationDeliveryMethod

    name = factory.Sequence(lambda n: f'notification_delivery_method_{n}')

    max_requests_per_period_0 = None
    request_period_seconds_0 = None

    max_requests_per_period_1 = None
    request_period_seconds_1 = None

    max_requests_per_period_2 = None
    request_period_seconds_2 = None
