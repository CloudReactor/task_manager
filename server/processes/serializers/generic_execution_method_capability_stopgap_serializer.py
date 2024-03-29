from typing import Any

from rest_framework import serializers

from ..models import Task


class GenericExecutionMethodCapabilityStopgapSerializer(serializers.Serializer):
    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            'execution_method_capability_details': data
        }

    def to_representation(self, instance: Task):
        return instance.execution_method_capability_details
