import logging

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, NotFound

from ..models import Workflow
from ..common.request_helpers import (
  extract_authenticated_run_environment
)
from ..exception import UnprocessableEntity

from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers
from .embedded_id_validating_serializer_mixin import (
    EmbeddedIdValidatingSerializerMixin
)

logger = logging.getLogger(__name__)

class EmbeddedWorkflowSerializer(EmbeddedIdValidatingSerializerMixin,
        SerializerHelpers, serializers.HyperlinkedModelSerializer):
    workflow = NameAndUuidSerializer(view_name='workflows-detail')

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)

        logger.info(f"super validated = {validated}")

        group = self.get_request_group()

        workflow_dict = data.get('workflow')

        if workflow_dict is None:
            if 'workflow' in data:
                raise serializers.ValidationError({
                    'workflow': [ErrorDetail('Cannot be empty', code='invalid')]
                })
        else:
            authenticated_run_environment = extract_authenticated_run_environment()
            try:
                workflow = Workflow.find_by_uuid_or_name(
                    workflow_dict, required_group=group,
                    required_run_environment=authenticated_run_environment)
                validated['workflow'] = workflow
            except (Workflow.DoesNotExist, NotFound) as e:
                raise UnprocessableEntity({
                    'workflow': [ErrorDetail('Workflow does not exist', code='not_found')]
                }) from e

        return validated

    def update(self, instance, validated_data):
        validated_workflow = validated_data.get('workflow')

        if validated_workflow and (instance.workflow != validated_workflow):
            raise UnprocessableEntity({
                'workflow': [ErrorDetail('Does not match existing', code='invalid')]
            })

        return super().update(instance, validated_data)
