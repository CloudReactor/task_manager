from typing import Any

from ..execution_methods import UnknownExecutionMethod

from .base_execution_method_serializer import (
    BaseExecutionMethodSerializer
)

class UnknownExecutionMethodSerializer(BaseExecutionMethodSerializer):
    def get_execution_method_type(self, obj) -> str:
        return UnknownExecutionMethod.NAME

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        return {}
