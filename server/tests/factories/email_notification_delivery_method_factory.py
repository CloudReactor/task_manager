from processes.models import EmailNotificationDeliveryMethod

import factory
from faker import Factory as FakerFactory

from .notification_delivery_method_factory import NotificationDeliveryMethodFactory
from .run_environment_factory import RunEnvironmentFactory

faker = FakerFactory.create()


class EmailNotificationDeliveryMethodFactory(NotificationDeliveryMethodFactory):
    class Meta:
        model = EmailNotificationDeliveryMethod

    name = factory.Sequence(lambda n: f'email_notification_delivery_method_{n}')
    description = faker.sentence()

    run_environment = factory.SubFactory(RunEnvironmentFactory,
        created_by_user=factory.SelfAttribute("..created_by_user"),
        created_by_group=factory.SelfAttribute("..created_by_group"))

    email_to_addresses = [faker.email()]
    email_cc_addresses = []
    email_bcc_addresses = []
