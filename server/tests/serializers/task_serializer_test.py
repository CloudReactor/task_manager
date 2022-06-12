from conftest import *

from processes.common.request_helpers import context_with_request
from processes.models import Task
from processes.serializers import TaskSerializer

import pytest

from moto import mock_ecs, mock_sts, mock_events


@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_basic_task_serialization(task_factory):
    task = cast(Task, task_factory())
    context = context_with_request()
    data = TaskSerializer(task, context=context).data
    validate_serialized_task(data, task)


@pytest.mark.django_db
@mock_ecs
@mock_sts
@mock_events
def test_task_serialization_with_unsupported_emc(task_factory):
    task = cast(Task, task_factory())
    task.execution_method_type = 'Voodoo'
    task.execution_method_capability_details = {
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
    assert validated['execution_method_capability_details'] == task.execution_method_capability_details
