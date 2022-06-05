from conftest import *

from processes.common.request_helpers import context_with_request
from processes.models import Task
from processes.serializers import TaskSerializer

import pytest


@pytest.mark.django_db
def test_basic_task_serialization(task_factory):
    task = cast(Task, task_factory())
    context = context_with_request()
    data = TaskSerializer(task, context=context).data
    validate_serialized_task(data, task)


@pytest.mark.django_db
def test_task_serialization_with_unsupported_emc(task_factory):
    task = cast(Task, task_factory())
    task.execution_method_type = 'Voodoo'
    task.execution_method_capability = {
        'type': 'Voodoo',
        'witch_id': 'DOLLY76'
    }

    context = context_with_authenticated_request(
        user=task.created_by_user,
        group=task.created_by_group
    )

    data = TaskSerializer(task, context=context).data
    validate_serialized_task(data, task)

    del data['uuid']

    ser = TaskSerializer(data=data, context=context)

    assert ser.is_valid() is True
    assert not ser.errors
    validated = ser.validated_data
    assert validated['execution_method_capability'] == task.execution_method_capability