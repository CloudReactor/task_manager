from django.utils import timezone

from processes.models import InsufficientServiceTaskExecutionsEvent

import factory
from pytest_factoryboy import register

from .group_factory import GroupFactory
from .task_factory import TaskFactory


@register
class InsufficientServiceTaskExecutionsEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InsufficientServiceTaskExecutionsEvent

    created_by_group = factory.SubFactory(GroupFactory)
    task = factory.SubFactory(TaskFactory)

    severity = InsufficientServiceTaskExecutionsEvent.Severity.ERROR
    interval_start_at = factory.LazyFunction(timezone.now)
    interval_end_at = factory.LazyFunction(timezone.now)
    detected_concurrency = 0
    required_concurrency = 1
