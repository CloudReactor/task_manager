import logging

from rest_framework import serializers

from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from ..models import WorkflowExecution

from .serializer_helpers import SerializerHelpers
from .embedded_workflow_serializer import EmbeddedWorkflowSerializer
from .workflow_task_instance_execution_serializer import WorkflowTaskInstanceExecutionSerializer
from .workflow_transition_evaluation_serializer import WorkflowTransitionEvaluationSerializer

logger = logging.getLogger(__name__)


@extend_schema_field(OpenApiTypes.STR)
class WorkflowExecutionStatusSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        return WorkflowExecution.Status(instance).name

    def to_internal_value(self, data):
        return WorkflowExecution.Status[data.upper()].value


class WorkflowExecutionSummarySerializer(serializers.HyperlinkedModelSerializer,
                                         SerializerHelpers):
    class Meta:
        model = WorkflowExecution
        fields = ('url', 'uuid', 'dashboard_url',
                  'status', 'run_reason',
                  'started_at', 'finished_at', 'last_heartbeat_at',
                  'stop_reason', 'marked_done_at',
                  'kill_started_at', 'kill_finished_at',
                  'kill_error_code',
                  'failed_attempts', 'timed_out_attempts',
                  'created_at', 'updated_at')

    url = serializers.HyperlinkedIdentityField(
        view_name='workflow_executions-detail',
        lookup_field='uuid'
    )
    status = WorkflowExecutionStatusSerializer()


class WorkflowExecutionSerializer(EmbeddedWorkflowSerializer):
    class Meta:
        model = WorkflowExecution
        fields = ('url',
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
                  'workflow',
                  'workflow_snapshot',
                  'workflow_task_instance_executions',
                  'workflow_transition_evaluations',
                  'created_at', 'updated_at')

    started_by = serializers.ReadOnlyField(source='started_by.username')
    marked_done_by = serializers.ReadOnlyField(
        source='marked_done_by.username')
    killed_by = serializers.ReadOnlyField(source='killed_by.username')
    url = serializers.HyperlinkedIdentityField(
        view_name='workflow_executions-detail',
        lookup_field='uuid'
    )
    status = WorkflowExecutionStatusSerializer()

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
