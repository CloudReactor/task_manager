from ..models import BasicEvent
from .event_serializer import EventSerializer


class BasicEventSerializer(EventSerializer):
    """
    Serializer for BasicEvent.
    BasicEvent has no additional fields beyond the base Event.
    """

    class Meta(EventSerializer.Meta):
        model = BasicEvent
        fields = EventSerializer.Meta.fields
