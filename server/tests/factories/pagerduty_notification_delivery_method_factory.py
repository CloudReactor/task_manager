from processes.models import PagerDutyNotificationDeliveryMethod

import factory
from faker import Factory as FakerFactory

from .notification_delivery_method_factory import NotificationDeliveryMethodFactory
from .run_environment_factory import RunEnvironmentFactory

faker = FakerFactory.create()


class PagerDutyNotificationDeliveryMethodFactory(NotificationDeliveryMethodFactory):
    class Meta:
        model = PagerDutyNotificationDeliveryMethod

    name = factory.Sequence(lambda n: f'pagerduty_notification_delivery_method_{n}')
    description = faker.sentence()

    run_environment = factory.SubFactory(RunEnvironmentFactory,
        created_by_user=factory.SelfAttribute("..created_by_user"),
        created_by_group=factory.SelfAttribute("..created_by_group"))

    pagerduty_api_key = 'test_api_key_12345'
    pagerduty_event_class_template = 'Task Execution Status Change'
    pagerduty_event_component_template = '{{ task_name }}'
    pagerduty_event_group_template = '{{ run_environment_name }}'
