from processes.models import WorkflowExecution

import factory

from .execution_factory import ExecutionFactory
from .workflow_factory import WorkflowFactory


class WorkflowExecutionFactory(ExecutionFactory):
    class Meta:
        model = WorkflowExecution

    workflow = factory.SubFactory(WorkflowFactory)
    status = WorkflowExecution.Status.RUNNING.value
    run_reason = 0
