from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail
from ..exception import UnprocessableEntity

class EmbeddedIdValidatingSerializerMixin(serializers.Serializer):
    def to_internal_value(self, data):
        id_attr = self.get_identity_attribute()
        request_id = data.pop(id_attr, None)

        if request_id:
            if self.instance:
                if str(getattr(self.instance, id_attr)) != request_id:
                    raise UnprocessableEntity({
                        id_attr: [ErrorDetail(f'{id_attr} does not match', code='invalid')]
                    })
            else:
                raise serializers.ValidationError({
                    id_attr: [ErrorDetail(f'{id_attr} may not be specified when creating',
                        code='not_allowed')]
                })

        return super().to_internal_value(data)

    def get_identity_attribute(self) -> str:
        return 'uuid'
