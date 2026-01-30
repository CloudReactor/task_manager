from processes.models import TaskExecution
from processes.models.convert_legacy_em_and_infra import populate_task_execution_em_and_infra

import factory
from faker import Factory as FakerFactory

from .execution_factory import ExecutionFactory
from .task_factory import TaskFactory
from .user_factory import UserFactory

faker = FakerFactory.create()


class TaskExecutionFactory(ExecutionFactory):
    class Meta:
        model = TaskExecution

    task = factory.SubFactory(TaskFactory)
    status = TaskExecution.Status.RUNNING.value
    run_reason = TaskExecution.RunReason.EXPLICIT_START.value
    stop_reason = None

    @factory.post_generation
    def sanitize_em(task_execution: TaskExecution, create: bool, extracted, **kwargs):
        populate_task_execution_em_and_infra(task_execution)
        task_execution.save()
