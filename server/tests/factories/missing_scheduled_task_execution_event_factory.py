from django.utils import timezone

from processes.models import MissingScheduledTaskExecutionEvent

import factory
from pytest_factoryboy import register

from .group_factory import GroupFactory
from .task_factory import TaskFactory


@register
class MissingScheduledTaskExecutionEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MissingScheduledTaskExecutionEvent

    created_by_group = factory.SubFactory(GroupFactory)
    task = factory.SubFactory(TaskFactory)

    severity = MissingScheduledTaskExecutionEvent.Severity.ERROR
    expected_execution_at = factory.LazyFunction(timezone.now)
