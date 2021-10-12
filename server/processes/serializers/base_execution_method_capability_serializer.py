from rest_framework import serializers
from rest_framework.fields import empty

from .base_execution_method_serializer import BaseExecutionMethodSerializer


class BaseExecutionMethodCapabilitySerializer(BaseExecutionMethodSerializer):
    def __init__(self, instance=None, data=empty, omit_details=False, **kwargs):
        if omit_details:
            super().__init__(instance, data,
                    fields=['type', 'capabilities'], **kwargs)
        else:
            super().__init__(instance, data, **kwargs)

    capabilities = serializers.SerializerMethodField(
            method_name='get_capabilities')

    def get_capabilities(self, obj) -> list[str]:
        return [c.name for c in obj.execution_method().capabilities()]
