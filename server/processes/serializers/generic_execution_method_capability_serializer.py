from typing import Any

from ..models import Task
from ..execution_methods import UnknownExecutionMethod

from .base_execution_method_capability_serializer import (
    BaseExecutionMethodCapabilitySerializer
)

class GenericExecutionMethodCapabilitySerializer(BaseExecutionMethodCapabilitySerializer):
    def get_execution_method_type(self, task: Task) -> str:
        return task.execution_method_type or UnknownExecutionMethod.NAME

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        rv = super().to_internal_value(data)
        rv['execution_method_capability'] = data
        return rv

    def to_representation(self, instance: Task):
        return instance.execution_method_capability

    def get_capabilities(self, obj) -> list[str]:
        return []
