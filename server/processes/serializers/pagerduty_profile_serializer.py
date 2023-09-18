from rest_framework import serializers

from ..models import PagerDutyProfile
from .embedded_id_validating_serializer_mixin import (
    EmbeddedIdValidatingSerializerMixin
)
from .group_setting_serializer_mixin import GroupSettingSerializerMixin


class PagerDutyProfileSerializer(GroupSettingSerializerMixin,
        EmbeddedIdValidatingSerializerMixin,
        serializers.HyperlinkedModelSerializer):
    """
    A PagerDutyProfile contains user-specific configuration on how to notify
    PagerDuty of events.
    """

    class Meta:
        model = PagerDutyProfile

        fields = ['url', 'uuid', 'name', 'description', 'dashboard_url',
                  'integration_key',
                  'default_event_severity',
                  'default_event_component_template',
                  'default_event_group_template',
                  'default_event_class_template',
                  'created_by_user', 'created_by_group', 'run_environment',
                  'created_at', 'updated_at']

        read_only_fields = [
            'url', 'uuid', 'dashboard_url',
            'created_by_user', 'created_by_group',
            'created_at', 'updated_at'
        ]

    url = serializers.HyperlinkedIdentityField(
        view_name='pagerduty_profiles-detail',
        lookup_field='uuid'
    )
