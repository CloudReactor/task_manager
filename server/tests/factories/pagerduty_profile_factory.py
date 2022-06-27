
from processes.models import PagerDutyProfile

import factory

from .owned_model_factory import OwnedModelFactory


class PagerDutyProfileFactory(OwnedModelFactory):
    class Meta:
        model = PagerDutyProfile

    name = factory.Sequence(lambda n: f'pdp_{n}')

    integration_key = factory.Faker('random_letters')
    default_event_severity = 'error'
