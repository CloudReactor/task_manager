import logging

from rest_framework import serializers

from ..models import WorkflowTaskInstanceExecution

from .name_and_uuid_serializer import NameAndUuidSerializer

logger = logging.getLogger(__name__)


class WorkflowTaskInstanceExecutionBaseSerializer(serializers.ModelSerializer):
    """
    WorkflowTaskInstanceExecutions hold the execution information
    for a WorkflowTaskInstance (which holds a Task) for a specific
    WorkflowExection (run of a Workflow).
    """

    class Meta:
        model = WorkflowTaskInstanceExecution
        fields = ('uuid', 'workflow_execution',
                  'workflow_task_instance', 'is_latest', 'created_at',)

    workflow_execution = NameAndUuidSerializer(
            view_name='workflow_executions-detail',
            include_name=False,
            read_only=True)

    workflow_task_instance = NameAndUuidSerializer(
            view_name='workflow_task_instances-detail',
            read_only=True)
