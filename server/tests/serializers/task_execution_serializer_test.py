from conftest import *

from processes.common.request_helpers import context_with_request
from processes.models import TaskExecution
from processes.serializers import TaskExecutionSerializer

import pytest


@pytest.mark.django_db
def test_basic_task_execution_serialization(task_execution_factory):
    task_execution = cast(TaskExecution, task_execution_factory())
    context = context_with_request()
    data = TaskExecutionSerializer(task_execution, context=context).data
    validate_serialized_task_execution(data, task_execution)

@pytest.mark.django_db
def test_task_execution_in_workflow_serialization(task_execution_factory,
        workflow_task_instance_execution_factory):
    task_execution = cast(TaskExecution, task_execution_factory())

    wtie = workflow_task_instance_execution_factory(
        task_execution=task_execution)

    context = context_with_request()
    data = TaskExecutionSerializer(task_execution, context=context).data

    validate_serialized_task_execution(data, task_execution)

    assert data['workflow_task_instance_execution']['uuid'] == str(wtie.uuid)