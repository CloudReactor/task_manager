from typing import Optional

import logging

from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.exceptions import (
    APIException,
    ErrorDetail,
    NotFound,
    PermissionDenied
)
from rest_framework.serializers import ValidationError

from ..common.request_helpers import ensure_group_access_level
from ..models import (
    UserGroupAccessLevel,
    Task,
    Workflow,
    WorkflowTaskInstance
)
from ..exception import UnprocessableEntity

from .name_and_uuid_serializer import NameAndUuidSerializer
from .embedded_workflow_serializer import EmbeddedWorkflowSerializer

logger = logging.getLogger(__name__)


class WorkflowTaskInstanceSerializer(EmbeddedWorkflowSerializer):
    """
    A WorkflowTaskInstance contains a Task that is configured to run in
    a Workflow.
    """
    
    class Meta:
        model = WorkflowTaskInstance
        fields = ('url', 'uuid', 'name', 'description',
                  'workflow', 'task', 'start_transition_condition',
                  'max_complete_executions', 'should_eval_transitions_after_first_execution',
                  'condition_count_threshold', 'condition_ratio_threshold',
                  'max_age_seconds', 'default_max_retries',
                  'failure_behavior', 'allow_workflow_execution_after_failure',
                  'timeout_behavior', 'allow_workflow_execution_after_timeout',
                  'environment_variables_overrides',
                  'allocated_cpu_units', 'allocated_memory_mb',
                  'use_task_alert_methods',
                  'ui_color', 'ui_icon_type', 'ui_scale',
                  'ui_center_margin_top', 'ui_center_margin_left',
                  'created_at', 'updated_at')

    task = NameAndUuidSerializer(view_name='tasks-detail', read_only=True)

    url = serializers.HyperlinkedIdentityField(
        view_name='workflow_task_instances-detail',
        lookup_field='uuid'
    )

    def __init__(self, instance=None, data=empty, workflow: Optional[Workflow] = None,
            for_embedded_deserialization=False, **kwargs):
        super().__init__(instance, data, **kwargs)
        self.embedded_in_workflow = workflow
        self.for_embedded_deserialization = for_embedded_deserialization

    def to_internal_value(self, data):
        group = self.get_request_group()
        validated = super().to_internal_value(data)

        workflow = self.embedded_in_workflow

        if self.instance:
            workflow = workflow or self.instance.workflow

            if self.embedded_in_workflow and (workflow != self.embedded_in_workflow):
                logger.error('WTI Serializer: embedded in workflow and instance workflow do not match')
                raise APIException()

        workflow_dict = data.get('workflow', None)
        explicit_workflow = None
        if workflow_dict:
            explicit_workflow = Workflow.find_by_uuid_or_name(workflow_dict, group,
                check_conflict=not self.for_embedded_deserialization)

            if workflow and (explicit_workflow.pk != workflow.pk):
                raise UnprocessableEntity({
                    'workflow': [
                        ErrorDetail('Cannot change Workflow', code='invalid')
                    ]
                })

        workflow = explicit_workflow or workflow

        if workflow is None:
            raise ValidationError({
                'workflow': [
                    ErrorDetail('Workflow is missing', code='missing')
                ]
            })

        try:
            ensure_group_access_level(group=workflow.created_by_group,
                min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                run_environment=workflow.run_environment)
        except PermissionDenied as pd:
            if self.for_embedded_deserialization:
                raise UnprocessableEntity({
                    'workflow': [
                        ErrorDetail(str(pd.detail), code='invalid')
                    ]
                }) from pd

            raise pd

        validated['workflow'] = workflow

        task_dict = data.get('task', None)
        if task_dict:
            try:
                validated['task'] = Task.find_by_uuid_or_name(task_dict, group,
                    required_run_environment=workflow.run_environment)
            except NotFound as nfe:
                raise UnprocessableEntity({
                    'task': [
                        ErrorDetail('Invalid Task', code='invalid')
                    ]
                }) from nfe


        return validated
