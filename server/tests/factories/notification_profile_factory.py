
from processes.models import NotificationProfile

import factory

from .owned_model_factory import OwnedModelFactory


class NotificationProfileFactory(OwnedModelFactory):
    class Meta:
        model = NotificationProfile

    name = factory.Sequence(lambda n: f'notification_profile_{n}')

    enabled = True

