
from processes.models import AlertMethod

import factory
from faker import Factory as FakerFactory

from .group_factory import GroupFactory
from .user_factory import UserFactory

faker = FakerFactory.create()


class AlertMethodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlertMethod

    name = factory.Sequence(lambda n: f'alert_method_{n}')

    created_by_group = factory.SubFactory(GroupFactory)
    created_by_user = factory.SubFactory(UserFactory)

    notify_on_success = False
    notify_on_failure = True
    notify_on_timeout = True
    error_severity_on_missing_execution = 'error'
    error_severity_on_missing_heartbeat = 'error'
    error_severity_on_service_down = 'error'

    enabled = True
