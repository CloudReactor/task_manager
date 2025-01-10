from processes.models import Notification, AlertSendStatus

import factory
from pytest_factoryboy import register

from .basic_event_factory import BasicEventFactory
from .group_factory import GroupFactory
from .notification_profile_factory import NotificationProfileFactory
from .email_notification_delivery_method_factory import EmailNotificationDeliveryMethodFactory


@register
class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    event = factory.SubFactory(BasicEventFactory)
    notification_profile = factory.SubFactory(NotificationProfileFactory,
      created_by_group=factory.SelfAttribute("..created_by_group"))
    notification_delivery_method = factory.SubFactory(EmailNotificationDeliveryMethodFactory,
      created_by_group=factory.SelfAttribute("..created_by_group"))

    created_by_group = factory.SubFactory(GroupFactory)

    send_status = AlertSendStatus.SENDING
