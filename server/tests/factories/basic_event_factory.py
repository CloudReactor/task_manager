from processes.models import BasicEvent, Event

import factory
from pytest_factoryboy import register

from .event_factory import EventFactory


@register
class BasicEventFactory(EventFactory):
    class Meta:
        model = BasicEvent

