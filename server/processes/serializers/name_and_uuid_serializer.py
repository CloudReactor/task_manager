from typing import Optional

from rest_framework import serializers

class NameAndUuidSerializer(serializers.Serializer):
    """
    Identifies an entity in three ways: 1. UUID; 2. Name; and 3. URL.
    When used to indentify an entity in a request method body, only one of
    uuid and name needs to be specified. If both are present, they must
    refer to the same entity or else the response will be a 400 error.
    """

    uuid = serializers.UUIDField(required=False)
    url = serializers.SerializerMethodField()
    name = serializers.CharField(required=False)

    def __init__(self, include_name=True, view_name=None,
                 context=None, **kwargs):
        self.view_name = view_name
        self.caller_context = context or {'request': None}
        super().__init__(**kwargs)

        if not include_name:
            self.fields.pop('name')

        self.url_field = serializers.HyperlinkedIdentityField(
                view_name=self.view_name,
                lookup_field='uuid')

    def get_url(self, obj) -> Optional[str]:
        # Doesn't work due to missing context, but can't find a way to inject it.
        # return self.url_field.to_representation(obj)
        return self.url_field.get_url(obj=obj, view_name=self.view_name,
                request=self.caller_context['request'],
                format=self.caller_context.get('format'))
