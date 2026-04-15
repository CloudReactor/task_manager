from processes.models import Execution, TaskExecution

import factory
from faker import Factory as FakerFactory

from .execution_factory import ExecutionFactory
from .task_factory import TaskFactory

faker = FakerFactory.create()


class TaskExecutionFactory(ExecutionFactory):
    class Meta:
        model = TaskExecution

    task = factory.SubFactory(TaskFactory)
    status = Execution.Status.RUNNING.value
    run_reason = TaskExecution.RunReason.EXPLICIT_START.value
    stop_reason = None
