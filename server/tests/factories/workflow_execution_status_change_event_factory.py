from processes.models import WorkflowExecutionStatusChangeEvent

import factory
from pytest_factoryboy import register

from .group_factory import GroupFactory
from .workflow_factory import WorkflowFactory
from .workflow_execution_factory import WorkflowExecutionFactory


@register
class WorkflowExecutionStatusChangeEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkflowExecutionStatusChangeEvent

    created_by_group = factory.SubFactory(GroupFactory)
    workflow = factory.SubFactory(WorkflowFactory)
    workflow_execution = factory.SubFactory(WorkflowExecutionFactory)

    severity = WorkflowExecutionStatusChangeEvent.Severity.INFO
