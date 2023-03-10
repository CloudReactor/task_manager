from typing import Any

from rest_framework import serializers
from rest_framework.fields import empty

from rest_flex_fields.serializers import FlexFieldsSerializerMixin


class BaseExecutionMethodSerializer(FlexFieldsSerializerMixin,
        serializers.Serializer):
    def __init__(self, instance=None, data=empty, omit_details=False, **kwargs):
        if omit_details:
            super().__init__(instance, data, fields=['type'], **kwargs)
        else:
            super().__init__(instance, data, **kwargs)


    type = serializers.SerializerMethodField(
            method_name='get_execution_method_type')

    def get_execution_method_type(self, obj: Any) -> str:
        raise NotImplementedError()
