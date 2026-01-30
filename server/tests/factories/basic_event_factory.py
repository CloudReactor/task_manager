from processes.models import BasicEvent, Event

import factory
from pytest_factoryboy import register

from .group_factory import GroupFactory


@register
class BasicEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BasicEvent

    created_by_group = factory.SubFactory(GroupFactory)

    severity = Event.Severity.ERROR
    error_summary = 'Error'
