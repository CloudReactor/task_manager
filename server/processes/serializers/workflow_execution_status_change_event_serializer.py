from typing import override

from rest_framework.exceptions import ErrorDetail

from ..exception.unprocessable_entity import UnprocessableEntity
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
    workflow = NameAndUuidSerializer(view_name='workflows-detail', required=False)
    workflow_execution = NameAndUuidSerializer(include_name=False, view_name='workflow_executions-detail', required=False)

    class Meta(ExecutionStatusChangeEventSerializer.Meta):
        model = WorkflowExecutionStatusChangeEvent
        fields = ExecutionStatusChangeEventSerializer.Meta.fields + [
            'workflow','workflow_execution',
        ]


    @override
    def to_internal_value(self, data):
        """Convert nested workflow and workflow_execution data to actual instances."""
        from ..models import RunEnvironment, Workflow, WorkflowExecution

        request = self.context.get('request')

        workflow_data = data.pop('workflow', None)
        workflow_execution_data = data.pop('workflow_execution', None)

        validated = super().to_internal_value(data)

        group = validated['created_by_group']
        run_environment = validated['run_environment']

        workflow_execution: WorkflowExecution | None = None
        if workflow_execution_data:
            workflow_execution = WorkflowExecution.find_by_uuid(workflow_execution_data,
                required_group=group, required_run_environment=run_environment)

        if workflow_execution is None:
            if self.instance:
                workflow_execution = self.instance.workflow_execution

            if workflow_execution is None:
                raise UnprocessableEntity({
                    'workflow_execution': [ErrorDetail('No Workflow Execution was found for the provided identifier', code='not_found')]
                })
        elif self.instance:
            if workflow_execution.pk != self.instance.workflow_execution.pk:
                raise UnprocessableEntity({
                    'workflow': [ErrorDetail('The specified Workflow Execution does not match the Workflow associated with the provided Event', code='mismatch')]
                })

        validated['workflow_execution'] = workflow_execution

        workflow: Workflow | None = None
        if workflow_data:
            workflow = Workflow.find_by_uuid_or_name(workflow_data,
                required_group=group,
                required_run_environment=run_environment)

            if workflow:
                if workflow.pk != workflow_execution.workflow.pk:
                    raise UnprocessableEntity({
                        'workflow': [ErrorDetail('The specified Workflow does not match the Workflow associated with the provided Workflow Execution', code='mismatch')]
                    })

        if workflow is None:
            workflow = workflow_execution.workflow

        if run_environment and (workflow.run_environment.pk != run_environment.pk):
            raise UnprocessableEntity({
                'workflow': [ErrorDetail('The Workflow\'s Run Environment does not match the specified Run Environment', code='mismatch')]
            })

        validated['workflow'] = workflow

        return validated