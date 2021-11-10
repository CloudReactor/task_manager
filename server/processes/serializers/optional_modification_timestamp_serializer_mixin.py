from rest_framework import serializers

class OptionalModificationTimestampSerializerMixin:
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)
