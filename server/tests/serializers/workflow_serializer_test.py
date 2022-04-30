from conftest import *

from processes.common.request_helpers import context_with_request
from processes.models import Workflow
from processes.serializers import WorkflowSerializer

import pytest


@pytest.mark.django_db
def test_basic_workflow_serialization(workflow_factory):
    workflow = cast(Workflow, workflow_factory())
    context = context_with_request()
    data = WorkflowSerializer(workflow, context=context).data
    validate_serialized_workflow(data, workflow)
