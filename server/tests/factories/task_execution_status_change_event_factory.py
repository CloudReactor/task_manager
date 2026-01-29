from processes.models import TaskExecutionStatusChangeEvent

import factory
from pytest_factoryboy import register

from .group_factory import GroupFactory
from .task_factory import TaskFactory
from .task_execution_factory import TaskExecutionFactory


@register
class TaskExecutionStatusChangeEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaskExecutionStatusChangeEvent

    created_by_group = factory.SubFactory(GroupFactory)
    task = factory.SubFactory(TaskFactory)
    task_execution = factory.SubFactory(TaskExecutionFactory)

    severity = TaskExecutionStatusChangeEvent.Severity.INFO
