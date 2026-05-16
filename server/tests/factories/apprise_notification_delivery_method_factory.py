from processes.models import AppriseNotificationDeliveryMethod

import factory
from faker import Factory as FakerFactory

from .notification_delivery_method_factory import NotificationDeliveryMethodFactory
from .run_environment_factory import RunEnvironmentFactory

faker = FakerFactory.create()


class AppriseNotificationDeliveryMethodFactory(NotificationDeliveryMethodFactory):
    class Meta:
        model = AppriseNotificationDeliveryMethod

    name = factory.Sequence(lambda n: f'apprise_notification_delivery_method_{n}')
    description = faker.sentence()

    run_environment = factory.SubFactory(RunEnvironmentFactory,
        created_by_user=factory.SelfAttribute("..created_by_user"),
        created_by_group=factory.SelfAttribute("..created_by_group"))

    apprise_url = 'slack://xoxb-test-token-here/C123456/U123456'
