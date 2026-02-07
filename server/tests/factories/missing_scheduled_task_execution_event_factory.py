from django.utils import timezone

from processes.models import MissingScheduledTaskExecutionEvent

import factory
from pytest_factoryboy import register

from .event_factory import EventFactory

from .task_factory import TaskFactory


@register
class MissingScheduledTaskExecutionEventFactory(EventFactory):
    class Meta:
        model = MissingScheduledTaskExecutionEvent

    task = factory.SubFactory(TaskFactory)

    expected_execution_at = factory.LazyFunction(timezone.now)
