import logging

from rest_framework import serializers

from rest_flex_fields.serializers import FlexFieldsSerializerMixin

from ..models import WorkflowTaskInstanceExecution

from .workflow_task_instance_execution_base_serializer import WorkflowTaskInstanceExecutionBaseSerializer
from .serializer_helpers import SerializerHelpers
from .task_execution_serializer import TaskExecutionSerializer

logger = logging.getLogger(__name__)


class WorkflowTaskInstanceExecutionSerializer(SerializerHelpers,
        FlexFieldsSerializerMixin, WorkflowTaskInstanceExecutionBaseSerializer):
    """
    WorkflowTaskInstanceExecutions hold the execution information
    for a WorkflowTaskInstance (which holds a Task) for a specific
    WorkflowExection (run of a Workflow).
    """

    class Meta:
        model = WorkflowTaskInstanceExecution
        fields = ('uuid', 'workflow_execution',
                  'workflow_task_instance', 'task_execution',
                  'is_latest', 'created_at')

    task_execution = TaskExecutionSerializer(read_only=True)
