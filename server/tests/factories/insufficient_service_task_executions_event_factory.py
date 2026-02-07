from django.utils import timezone

from processes.models import InsufficientServiceTaskExecutionsEvent

import factory
from pytest_factoryboy import register

from .event_factory import EventFactory
from .task_factory import TaskFactory


@register
class InsufficientServiceTaskExecutionsEventFactory(EventFactory):
    class Meta:
        model = InsufficientServiceTaskExecutionsEvent

    task = factory.SubFactory(TaskFactory)

    severity = InsufficientServiceTaskExecutionsEvent.Severity.ERROR
    interval_start_at = factory.LazyFunction(timezone.now)
    interval_end_at = factory.LazyFunction(timezone.now)
    detected_concurrency = 0
    required_concurrency = 1
