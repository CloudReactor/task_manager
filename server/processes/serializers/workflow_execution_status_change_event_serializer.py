from ..models import WorkflowExecutionStatusChangeEvent
from .execution_status_change_event_serializer import ExecutionStatusChangeEventSerializer
from .name_and_uuid_serializer import NameAndUuidSerializer
from .workflow_execution_serializer import WorkflowExecutionStatusSerializer


class WorkflowExecutionStatusChangeEventSerializer(ExecutionStatusChangeEventSerializer):
    """
    Serializer for WorkflowExecutionStatusChangeEvent.
    Includes workflow execution reference in addition to status change fields.
    """

    status = WorkflowExecutionStatusSerializer()
    workflow_execution = NameAndUuidSerializer(view_name='workflow_executions-detail', required=False)

    class Meta(ExecutionStatusChangeEventSerializer.Meta):
        model = WorkflowExecutionStatusChangeEvent
        fields = ExecutionStatusChangeEventSerializer.Meta.fields + [
            'workflow_execution',
        ]
