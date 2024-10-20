import logging

from rest_framework import serializers

from ..models import NotificationProfile

from .name_and_uuid_serializer import NameAndUuidSerializer
from .embedded_id_validating_serializer_mixin import (
    EmbeddedIdValidatingSerializerMixin
)
from .group_serializer import GroupSerializer
from .group_setting_serializer_mixin import GroupSettingSerializerMixin

logger = logging.getLogger(__name__)


class NotificationProfileSerializer(GroupSettingSerializerMixin,
        EmbeddedIdValidatingSerializerMixin, serializers.HyperlinkedModelSerializer):
    """
    A serializer for NotificationProfile objects.
    """

    class Meta:
        model = NotificationProfile
        fields = ['url', 'uuid', 'name', 'description', 'dashboard_url',
                  'enabled', 'notification_delivery_methods',
                  'created_by_user', 'created_by_group', 'run_environment',
                  'created_at', 'updated_at']

        read_only_fields = [
            'url', 'uuid', 'dashboard_url',
            'created_by_user', 'created_by_group',
            'created_at', 'updated_at'
        ]

    url = serializers.HyperlinkedIdentityField(
            view_name='notification_profiles-detail',
            lookup_field='uuid'
    )

    created_by_user = serializers.ReadOnlyField(source='created_by_user.username')
    created_by_group = GroupSerializer(read_only=True, include_users=False)

    notification_delivery_methods = NameAndUuidSerializer(
            include_name=True,
            view_name='notification_delivery_methods-detail',
            many=True, required=False)
