from typing import Any

from ..execution_methods import UnknownExecutionMethod

from .base_execution_method_capability_serializer import (
    BaseExecutionMethodCapabilitySerializer
)

class UnknownExecutionMethodCapabilitySerializer(BaseExecutionMethodCapabilitySerializer):
    def get_execution_method_type(self, obj: Any) -> str:
        return UnknownExecutionMethod.NAME
    
    def get_capabilities(self, obj: Any) -> list[str]:
        return []
