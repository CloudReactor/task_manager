from ..models import TaskExecutionStatusChangeEvent
from .execution_status_change_event_serializer import ExecutionStatusChangeEventSerializer
from .name_and_uuid_serializer import NameAndUuidSerializer
from .task_execution_serializer import TaskExecutionStatusSerializer


class TaskExecutionStatusChangeEventSerializer(ExecutionStatusChangeEventSerializer):
    """
    Serializer for TaskExecutionStatusChangeEvent.
    Includes task execution reference in addition to status change fields.
    """

    status = TaskExecutionStatusSerializer()
    task_execution = NameAndUuidSerializer(view_name='task_executions-detail', required=False)

    class Meta(ExecutionStatusChangeEventSerializer.Meta):
        model = TaskExecutionStatusChangeEvent
        fields = ExecutionStatusChangeEventSerializer.Meta.fields + [
            'task_execution',
        ]
