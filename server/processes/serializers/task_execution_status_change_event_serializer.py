from typing import override

from rest_framework.exceptions import ErrorDetail

from ..exception.unprocessable_entity import UnprocessableEntity
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
    task = NameAndUuidSerializer(view_name='tasks-detail', required=False)
    task_execution = NameAndUuidSerializer(include_name=False, view_name='task_executions-detail', required=False)

    class Meta(ExecutionStatusChangeEventSerializer.Meta):
        model = TaskExecutionStatusChangeEvent
        fields = ExecutionStatusChangeEventSerializer.Meta.fields + [
            'task','task_execution',
        ]

    @override
    def to_internal_value(self, data):
        """Convert nested task and task_execution data to actual instances."""        
        from ..models import Task, TaskExecution

        task_data = data.pop('task', None)
        task_execution_data = data.pop('task_execution', None)

        validated = super().to_internal_value(data)

        group = validated['created_by_group']
        run_environment = validated['run_environment']

        task_execution: TaskExecution | None = None
        if task_execution_data:
            task_execution = TaskExecution.find_by_uuid(task_execution_data,
                required_group=group, required_run_environment=run_environment)                                                               
            
        if task_execution is None:        
            if self.instance:
                task_execution = self.instance.task_execution
        elif self.instance and self.instance.task_execution:
            if task_execution.pk != self.instance.task_execution.pk:
                raise UnprocessableEntity({
                    'task': [ErrorDetail('The specified Task Execution does not match the Task associated with the provided Event', code='mismatch')]
                })
        
        if task_execution is None:
            raise UnprocessableEntity({
                'task_execution': [ErrorDetail('No Task Execution was found for the provided identifier', code='not_found')]
            })

        validated['task_execution'] = task_execution

        task: Task | None = None
        if task_data:
            task = Task.find_by_uuid_or_name(task_data,
                required_group=group,
                required_run_environment=run_environment)
                        
            if task:
                if task.pk != task_execution.task.pk:
                    raise UnprocessableEntity({
                        'task': [ErrorDetail('The specified Task does not match the Task associated with the provided Task Execution', code='mismatch')]
                    })
                
        if task is None:                
            task = task_execution.task

        if task:
            if run_environment:
                if task.run_environment.pk != run_environment.pk:
                    raise UnprocessableEntity({
                        'task': [ErrorDetail('The Task\'s Run Environment does not match the specified Run Environment', code='mismatch')]
                    })
            else:
                run_environment = task.run_environment
                validated['run_environment'] = run_environment
                                
        validated['task'] = task        

        return validated
