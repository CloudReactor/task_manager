from typing import Any, Optional

import logging

from rest_framework import serializers
from rest_framework.exceptions import (
    ErrorDetail, NotFound, ValidationError
)

from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema_field,
    # PolymorphicProxySerializer,
)

from ..models import (
  AlertMethod,
  EmailNotificationProfile,
  PagerDutyProfile
)

from ..exception import UnprocessableEntity

from .name_and_uuid_serializer import NameAndUuidSerializer
from .embedded_id_validating_serializer_mixin import (
    EmbeddedIdValidatingSerializerMixin
)
from .group_serializer import GroupSerializer
from .group_setting_serializer_mixin import GroupSettingSerializerMixin

logger = logging.getLogger(__name__)


class AlertMethodSerializer(GroupSettingSerializerMixin,
        EmbeddedIdValidatingSerializerMixin, serializers.HyperlinkedModelSerializer):
    """
    An AlertMethod specifies one or more configured methods of notifying
    users or external sources of events that trigger when one or more
    conditions are satisfied.
    """

    METHOD_TYPE_EMAIL = 'email'
    METHOD_TYPE_PAGERDUTY = 'PagerDuty'

    class Meta:
        model = AlertMethod
        fields = ['url', 'uuid', 'name', 'description', 'dashboard_url',
                  'enabled',
                  'method_details',
                  'notify_on_success', 'notify_on_failure', 'notify_on_timeout',
                  'error_severity_on_missing_execution',
                  'error_severity_on_missing_heartbeat',
                  'error_severity_on_service_down',
                  'created_by_user', 'created_by_group', 'run_environment',
                  'created_at', 'updated_at']

        read_only_fields = [
            'url', 'uuid', 'dashboard_url',
            'created_by_user', 'created_by_group',
            'created_at', 'updated_at'
        ]

    url = serializers.HyperlinkedIdentityField(
            view_name='alert_methods-detail',
            lookup_field='uuid'
    )
    method_details = serializers.SerializerMethodField()

    created_by_user = serializers.ReadOnlyField(source='created_by_user.username')
    created_by_group = GroupSerializer(read_only=True, include_users=False)

    # TODO: improve this
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_method_details(self, obj: AlertMethod) -> Optional[dict[str, Any]]:
        if obj.email_notification_profile:
            profile = NameAndUuidSerializer(instance=obj.email_notification_profile,
                                            view_name='email_notification_profiles-detail',
                                            context=self.context).data
            return {
                'type': AlertMethodSerializer.METHOD_TYPE_EMAIL,
                'profile': profile,
            }
        elif obj.pagerduty_profile:
            profile = NameAndUuidSerializer(instance=obj.pagerduty_profile,
                                            view_name='pagerduty_profiles-detail',
                                            context=self.context).data
            return {
                'type':  AlertMethodSerializer.METHOD_TYPE_PAGERDUTY,
                'profile': profile,
                'event_severity': obj.pagerduty_event_severity,
                'event_group_template': obj.pagerduty_event_group_template,
                'event_class_template': obj.pagerduty_event_class_template
            }

        return None

    def to_internal_value(self, data):
        method_details_dict = data.pop('method_details', None)
        validated = super().to_internal_value(data)

        group = validated['created_by_group']
        run_environment = validated.get('run_environment')

        method_type: Optional[str] = None
        if method_details_dict:
            method_type = method_details_dict.get('type')

        if not method_type and self.instance:
            method_type = self.method_type_of_instance(self.instance)
            if not method_type:
                raise ValidationError({
                    'method_details': [
                        ErrorDetail('No method type found', code='missing')
                    ]
                })

        if method_details_dict:
            profile_dict = method_details_dict.get('profile')

            if profile_dict is not None:
                try:
                    if method_type == AlertMethodSerializer.METHOD_TYPE_PAGERDUTY:
                        validated['pagerduty_profile'] = PagerDutyProfile.find_by_uuid_or_name(
                            profile_dict, required_group=group,
                            required_run_environment=run_environment)

                        for prop_name in ['event_severity', 'event_component_template', 'event_group_template', 'event_class_template']:
                            v = method_details_dict.get(prop_name)
                            if v is not None:
                                validated[f"pagerduty_{prop_name}"] = v

                        # TODO clear all other profile links programmatically
                        validated['email_notification_profile'] = None
                    elif method_type == AlertMethodSerializer.METHOD_TYPE_EMAIL:
                        validated['email_notification_profile'] = EmailNotificationProfile.find_by_uuid_or_name(
                            profile_dict, required_group=group,
                            required_run_environment=run_environment)

                        validated['pagerduty_profile'] = None
                except NotFound as nfe:
                    raise UnprocessableEntity({
                        'method_details': [
                            ErrorDetail('Method profile not found', code='invalid')
                        ]
                    }) from nfe

        return validated

    def method_type_of_instance(self, alert_method: AlertMethod) -> Optional[str]:
        if alert_method.pagerduty_profile:
            return AlertMethodSerializer.METHOD_TYPE_PAGERDUTY

        if alert_method.email_notification_profile:
            return AlertMethodSerializer.METHOD_TYPE_EMAIL

        return None
