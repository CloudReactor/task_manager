from rest_framework import serializers

from .event_serializer import EventSerializer


class ExecutionStatusChangeEventSerializer(EventSerializer):
    """
    Abstract serializer for ExecutionStatusChangeEvent subclasses.
    Includes status change specific fields in addition to base Event fields.
    """

    class Meta(EventSerializer.Meta):
        # Abstract serializer - subclasses must specify model
        abstract = True
        fields = EventSerializer.Meta.fields + [
            'status',
            'postponed_until',
            'count_with_same_status_after_postponement',
            'count_with_success_status_after_postponement',
            'triggered_at',
        ]
