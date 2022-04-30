import logging

from rest_framework import serializers

from drf_spectacular.utils import extend_schema_field

from ..models import WorkflowExecution

from .serializer_helpers import SerializerHelpers
from .embedded_workflow_serializer import EmbeddedWorkflowSerializer
from .workflow_task_instance_execution_serializer import WorkflowTaskInstanceExecutionSerializer
from .workflow_transition_evaluation_serializer import WorkflowTransitionEvaluationSerializer

logger = logging.getLogger(__name__)


@extend_schema_field(serializers.ChoiceField(choices=[
        status.name for status in list(WorkflowExecution.Status)]),
        component_name='WorkflowExecutionStatus')
class WorkflowExecutionStatusSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        return WorkflowExecution.Status(instance).name

    def to_internal_value(self, data):
        return WorkflowExecution.Status[data.upper()].value


@extend_schema_field(serializers.ChoiceField(choices=[
        reason.name for reason in list(WorkflowExecution.RunReason)]),
        component_name='WorkflowExecutionRunReason')
class WorkflowExecutionRunReasonSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        return WorkflowExecution.RunReason(instance).name

    def to_internal_value(self, data):
        return WorkflowExecution.RunReason[data.upper()].value


@extend_schema_field(serializers.ChoiceField(choices=[
        reason.name for reason in list(WorkflowExecution.StopReason)]),
        component_name='WorkflowExecutionStopReason')
class WorkflowExecutionStopReasonSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        return WorkflowExecution.StopReason(instance).name

    def to_internal_value(self, data):
        return WorkflowExecution.StopReason[data.upper()].value


class WorkflowExecutionSummarySerializer(serializers.HyperlinkedModelSerializer,
                                         SerializerHelpers):
    """
    A WorkflowExecutionSummary contains a subset of the data inside of a
    WorkflowExecution.
    """

    class Meta:
        model = WorkflowExecution
        fields = [
            'url', 'uuid', 'dashboard_url',
            'status', 'run_reason',
            'started_at', 'finished_at', 'last_heartbeat_at',
            'stop_reason', 'marked_done_at',
            'kill_started_at', 'kill_finished_at',
            'kill_error_code',
            'failed_attempts', 'timed_out_attempts',
            'created_at', 'updated_at'
        ]

    url = serializers.HyperlinkedIdentityField(
        view_name='workflow_executions-detail',
        lookup_field='uuid'
    )
    status = WorkflowExecutionStatusSerializer()
    run_reason = WorkflowExecutionRunReasonSerializer(required=False)
    stop_reason = WorkflowExecutionStopReasonSerializer(required=False)


class WorkflowExecutionSerializer(EmbeddedWorkflowSerializer):
    """
    A WorkflowExecution holds data on a specific execution (run) of a Workflow.
    """

    class Meta:
        model = WorkflowExecution
        fields = [
            'url',
            'uuid', 'dashboard_url',
            'workflow',
            'status',
            'run_reason',
            'started_at',
            'started_by',
            'finished_at',
            'last_heartbeat_at',
            'stop_reason',
            'marked_done_at',
            'marked_done_by',
            'kill_started_at',
            'killed_by',
            'kill_finished_at',
            'kill_error_code',
            'failed_attempts', 'timed_out_attempts',
            'workflow_snapshot',
            'workflow_task_instance_executions',
            'workflow_transition_evaluations',
            'created_at', 'updated_at'
        ]

        read_only_fields = [
            'url', 'uuid', 'dashboard_url',
            'created_by_user', 'created_by_group',
            'workflow_snapshot',
            'workflow_task_instance_executions',
            'workflow_transition_evaluations',
            'created_at', 'updated_at'
        ]

    started_by = serializers.ReadOnlyField(source='started_by.username',
        allow_null=True)
    marked_done_by = serializers.ReadOnlyField(
        source='marked_done_by.username', allow_null=True)
    killed_by = serializers.ReadOnlyField(source='killed_by.username',
        allow_null=True)
    url = serializers.HyperlinkedIdentityField(
        view_name='workflow_executions-detail',
        lookup_field='uuid'
    )
    status = WorkflowExecutionStatusSerializer()
    run_reason = WorkflowExecutionRunReasonSerializer(required=False)
    stop_reason = WorkflowExecutionStopReasonSerializer(required=False)

    workflow_task_instance_executions = WorkflowTaskInstanceExecutionSerializer(many=True, read_only=True)
    workflow_transition_evaluations = WorkflowTransitionEvaluationSerializer(many=True, read_only=True)

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        validated['started_by'] = self.get_request_user()
        return validated

    def update(self, instance, validated):
        request_status = WorkflowExecution.Status(validated.get(
            'status', WorkflowExecution.Status.RUNNING.value))
        existing_status = WorkflowExecution.Status(instance.status)

        if request_status == WorkflowExecution.Status.RUNNING:
            if existing_status != WorkflowExecution.Status.RUNNING:
                raise serializers.ValidationError(
                    {'status': f"Status cannot be set to {request_status.name} after {existing_status.name}"})
        elif request_status == WorkflowExecution.Status.STOPPING:
            pass
        else:
            raise serializers.ValidationError(
                {'status': f"Status cannot be set to {request_status.name} after {existing_status.name}"})

        return super().update(instance, validated)
