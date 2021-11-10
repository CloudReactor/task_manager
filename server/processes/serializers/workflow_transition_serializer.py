from typing import Optional

import logging

from rest_framework import serializers
from rest_framework.exceptions import (
    ErrorDetail,
    NotFound
)
from ..exception import UnprocessableEntity
from ..models import (
    UserGroupAccessLevel, Workflow,
    WorkflowTaskInstance, WorkflowTransition
)
from ..common.request_helpers import (
  extract_authenticated_run_environment,
  ensure_group_access_level
)
from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers
from .embedded_workflow_serializer import EmbeddedIdValidatingSerializerMixin

logger = logging.getLogger(__name__)


class WorkflowTransitionSerializer(EmbeddedIdValidatingSerializerMixin,
        serializers.HyperlinkedModelSerializer, SerializerHelpers):
    """
    A WorkflowTransition is a directed edge in a Worfklow, which is a directed
    graph. It contains a source WorkflowTaskInstance, a destination
    WorkflowTaskInstance, as well as conditions for triggering the destination
    to execution.
    """

    class Meta:
        model = WorkflowTransition
        fields = ('url', 'uuid', 'description',
                  'from_workflow_task_instance',
                  'to_workflow_task_instance',
                  'rule_type', 'exit_codes', 'threshold_property',
                  'custom_expression', 'priority',
                  'ui_color', 'ui_line_style', 'ui_scale',
                  'created_at', 'updated_at')

    from_workflow_task_instance = NameAndUuidSerializer(
            view_name='workflow_task_instances-detail')

    to_workflow_task_instance = NameAndUuidSerializer(
            view_name='workflow_task_instances-detail')

    url = serializers.HyperlinkedIdentityField(
        view_name='workflow_transitions-detail',
        lookup_field='uuid', read_only=True, required=False
    )

    def to_internal_value(self, data):
        group = self.get_request_group()
        authenticated_run_environment = extract_authenticated_run_environment()
        validated = super().to_internal_value(data)

        logger.debug(f"wts: to_internal value, validated = {validated}")

        #workflow = self.instance.workflow if self.instance else None

        from_workflow: Optional[Workflow] = None
        last_present_property_name: Optional[str] = None

        for x in ['from', 'to']:
            is_to = (x == 'to')
            workflow: Optional[Workflow] = None

            p = f'{x}_workflow_task_instance'

            if p in data:
                last_present_property_name = p
                wti_dict = data[p]

                if not wti_dict:
                    raise serializers.ValidationError({
                        p: [
                            ErrorDetail('Workflow Task Instance must not be null', code='invalid')
                        ]
                    })

                try:
                    wti = WorkflowTaskInstance.find_by_uuid_or_name(
                            obj_dict=wti_dict,
                            required_group=group,
                            required_run_environment=authenticated_run_environment)
                except NotFound as nfe:
                    raise UnprocessableEntity({
                        p: [
                            ErrorDetail('Workflow Task Instance was not found or not accessible', code='not_found')
                        ]
                    }) from nfe

                if wti:
                    workflow = wti.workflow

                    ensure_group_access_level(group=workflow.created_by_group,
                        min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                        run_environment=workflow.run_environment)

                    validated[f'{x}_workflow_task_instance'] = wti
                elif not self.instance:
                    raise serializers.ValidationError({
                        p: [
                            ErrorDetail('Workflow Task Instance is missing', code='missing')
                        ]
                    })
            else:
                if not self.instance:
                    raise serializers.ValidationError({
                        p: [
                            ErrorDetail('Workflow Task Instance must be specified', code='missing')
                        ]
                    })

            if workflow is None:
                if is_to:
                    workflow = self.instance.to_workflow_task_instance.workflow
                else:
                    workflow = self.instance.from_workflow_task_instance.workflow

            if is_to:
                if workflow != from_workflow:
                    # TODO: test this case
                    last_present_property_name = last_present_property_name or \
                            'from_workflow_task_instance'

                    raise serializers.ValidationError({
                        last_present_property_name: [
                            ErrorDetail('Workflow Task Instances must be associated with the same Workflow', code='invalid')
                        ]
                    })
            else:
                from_workflow = workflow

        return validated
