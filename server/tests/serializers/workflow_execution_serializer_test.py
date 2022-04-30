from conftest import *

from processes.common.request_helpers import context_with_request
from processes.models import WorkflowExecution
from processes.serializers import WorkflowExecutionSerializer

import pytest


@pytest.mark.django_db
def test_basic_workflow_execution_serialization(workflow_execution_factory):
    workflow_execution = cast(WorkflowExecution, workflow_execution_factory())
    context = context_with_request()
    data = WorkflowExecutionSerializer(workflow_execution, context=context).data

    print(data)


    validate_serialized_workflow_execution(data, workflow_execution)


@pytest.mark.django_db
def test_basic_workflow_execution_summary_serialization(
        workflow_execution_factory):
    workflow_execution = cast(WorkflowExecution, workflow_execution_factory())
    context = context_with_request()
    data = WorkflowExecutionSummarySerializer(workflow_execution,
            context=context).data
    validate_serialized_workflow_execution_summary(data, workflow_execution)
