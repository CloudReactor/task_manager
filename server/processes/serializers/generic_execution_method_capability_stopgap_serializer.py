from typing import Any

from rest_framework import serializers
from rest_framework.fields import empty

from ..models import Task


class GenericExecutionMethodCapabilityStopgapSerializer(serializers.Serializer):
    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            'execution_method_capability': data
        }

    def to_representation(self, instance: Task):
        return instance.execution_method_capability_details
