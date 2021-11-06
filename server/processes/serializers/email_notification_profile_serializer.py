from rest_framework import serializers

from ..models import EmailNotificationProfile
from .embedded_id_validating_serializer_mixin import (
    EmbeddedIdValidatingSerializerMixin
)

from .group_setting_serializer_mixin import GroupSettingSerializerMixin


class EmailNotificationProfileSerializer(GroupSettingSerializerMixin,
        EmbeddedIdValidatingSerializerMixin,
        serializers.HyperlinkedModelSerializer):
    """
    An EmailProfile contains settings for emailing notifications.
    """

    class Meta:
        model = EmailNotificationProfile
        fields = ['url', 'uuid', 'name', 'description', 'dashboard_url',
                  'created_by_user', 'created_by_group', 'run_environment',
                  'created_at', 'updated_at',
                  'to_addresses', 'cc_addresses', 'bcc_addresses',
                  'subject_template', 'body_template']

    url = serializers.HyperlinkedIdentityField(
        view_name='email_notification_profiles-detail',
        lookup_field='uuid'
    )
