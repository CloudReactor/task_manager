from processes.models import TaskExecution, TaskExecutionStatusChangeEvent

import factory
from pytest_factoryboy import register

from .event_factory import EventFactory
from .task_factory import TaskFactory
from .task_execution_factory import TaskExecutionFactory


@register
class TaskExecutionStatusChangeEventFactory(EventFactory):
    class Meta:
        model = TaskExecutionStatusChangeEvent

    task = factory.SubFactory(TaskFactory)
    task_execution = factory.SubFactory(TaskExecutionFactory)

    status = TaskExecution.Status.FAILED
