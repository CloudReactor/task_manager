from processes.models import WorkflowTaskInstanceExecution

import factory

from .task_execution_factory import TaskExecutionFactory
from .workflow_execution_factory import WorkflowExecutionFactory
from .workflow_task_instance_factory import WorkflowTaskInstanceFactory


class WorkflowTaskInstanceExecutionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkflowTaskInstanceExecution

    workflow_execution = factory.SubFactory(WorkflowExecutionFactory)

    workflow_task_instance = factory.SubFactory(WorkflowTaskInstanceFactory)

    task_execution = factory.SubFactory(TaskExecutionFactory)

    is_latest = True
