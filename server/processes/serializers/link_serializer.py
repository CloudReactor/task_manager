from rest_framework import serializers


class LinkSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    link_url_template = serializers.CharField()
    link_url = serializers.CharField(read_only=True)
    icon_url = serializers.CharField(read_only=True)
    description = serializers.CharField()
    rank = serializers.IntegerField()
