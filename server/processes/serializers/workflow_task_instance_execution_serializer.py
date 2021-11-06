import logging

from rest_framework import serializers

from rest_flex_fields.serializers import FlexFieldsSerializerMixin

from ..models import WorkflowTaskInstanceExecution

from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers
from .task_execution_serializer import  TaskExecutionSerializer

logger = logging.getLogger(__name__)


class WorkflowTaskInstanceExecutionSerializer(SerializerHelpers,
        FlexFieldsSerializerMixin, serializers.ModelSerializer):
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

    workflow_execution = NameAndUuidSerializer(
            view_name='workflow_executions-detail',
            include_name=False,
            read_only=True)

    workflow_task_instance = NameAndUuidSerializer(
            view_name='workflow_task_instances-detail',
            read_only=True)

    task_execution = TaskExecutionSerializer()
