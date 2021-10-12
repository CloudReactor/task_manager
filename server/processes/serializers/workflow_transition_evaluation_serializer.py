from typing import Optional

import logging

from rest_framework import serializers

from processes.models import (
        WorkflowTransitionEvaluation,
)

from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers

logger = logging.getLogger(__name__)


class WorkflowTransitionEvaluationSerializer(serializers.ModelSerializer,
                                             SerializerHelpers):
    class Meta:
        model = WorkflowTransitionEvaluation
        fields = ('uuid', 'result',
                  'workflow_transition', 'workflow_execution',
                  'from_workflow_task_instance_execution',
                  'evaluated_at')

    workflow_transition = NameAndUuidSerializer(
          view_name='workflow_transitions-detail', read_only=True,
          include_name=False)

    from_workflow_task_instance_execution = serializers.SerializerMethodField()

    def get_from_workflow_task_instance_execution(self, wte: WorkflowTransitionEvaluation) -> Optional[str]:
        wtie = wte.from_workflow_task_instance_execution
        if wtie:
            return str(wtie.uuid)

        return None

    workflow_execution = NameAndUuidSerializer(
            view_name='workflow_executions-detail',
            read_only=True,
            include_name=False)
