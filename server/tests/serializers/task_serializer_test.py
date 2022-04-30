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
