from typing import List

from processes.models import EmailNotificationProfile

import factory

from .owned_model_factory import OwnedModelFactory


class EmailNotificationProfileFactory(OwnedModelFactory):
    class Meta:
        model = EmailNotificationProfile        

    name = factory.Sequence(lambda n: f'pdp_{n}')

    subject_template = factory.Faker('random_letters')
    body_template = factory.Faker('random_letters')
    to_addresses = [factory.Faker('ascii_company_email')]
    cc_addresses: List[str] = []
    bcc_addresses: List[str] = []
