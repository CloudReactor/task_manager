from processes.models import Execution, WorkflowExecution

import factory

from .execution_factory import ExecutionFactory
from .workflow_factory import WorkflowFactory


class WorkflowExecutionFactory(ExecutionFactory):
    class Meta:
        model = WorkflowExecution

    workflow = factory.SubFactory(WorkflowFactory)
    status = Execution.Status.RUNNING.value
    run_reason = 0
