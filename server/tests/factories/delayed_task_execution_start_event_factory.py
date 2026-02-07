from django.utils import timezone

from processes.models import DelayedTaskExecutionStartEvent

import factory
from pytest_factoryboy import register

from .group_factory import GroupFactory
from .task_factory import TaskFactory
from .task_execution_factory import TaskExecutionFactory


@register
class DelayedTaskExecutionStartEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DelayedTaskExecutionStartEvent

    created_by_group = factory.SubFactory(GroupFactory)
    task = factory.SubFactory(TaskFactory)
    task_execution = factory.SubFactory(TaskExecutionFactory)

    severity = DelayedTaskExecutionStartEvent.Severity.WARNING
    desired_start_at = factory.LazyFunction(timezone.now)
    expected_start_by_deadline = factory.LazyFunction(timezone.now)
