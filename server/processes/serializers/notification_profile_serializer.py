from typing import override

import logging

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, NotFound

from ..models import NotificationProfile
from ..exception import UnprocessableEntity

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

    @override
    def to_internal_value(self, data):
        """Convert notification_delivery_methods from dicts with UUIDs to actual model instances."""
        validated = super().to_internal_value(data)

        # Convert notification_delivery_methods dicts to model instances
        run_environment = validated.get('run_environment')
        self.set_validated_notification_delivery_methods(
            data=data,
            validated=validated,
            run_environment=run_environment
        )

        return validated

    def set_validated_notification_delivery_methods(self, data, validated,
            run_environment):
        """Convert notification_delivery_methods dicts to model instances."""
        from ..models import NotificationDeliveryMethod

        group = validated['created_by_group']
        body_notification_delivery_methods = data.get('notification_delivery_methods')

        if body_notification_delivery_methods is not None:
            updated_notification_delivery_methods = []

            for body_notification_delivery_method in body_notification_delivery_methods:
                try:
                    ndm = NotificationDeliveryMethod.find_by_uuid_or_name(
                        body_notification_delivery_method,
                        required_group=group,
                        allowed_run_environment=run_environment,
                        allow_any_run_environment=False
                    )
                except serializers.ValidationError as validation_error:
                    # Re-raise with proper field name
                    if hasattr(validation_error, 'detail'):
                        detail = validation_error.detail
                        if isinstance(detail, list) and len(detail) == 1:
                            raise serializers.ValidationError({
                                'notification_delivery_methods': [str(detail[0])]
                            })
                    raise validation_error
                except NotFound as nfe:
                    raise UnprocessableEntity({
                        'notification_delivery_methods': [
                            ErrorDetail('Notification Delivery Method not found', code='invalid')
                        ]
                    }) from nfe

                updated_notification_delivery_methods.append(ndm)

            validated['notification_delivery_methods'] = updated_notification_delivery_methods

    @override
    def create(self, validated_data):
        return self.create_or_update(None, validated_data)

    @override
    def update(self, instance, validated_data):
        return self.create_or_update(instance, validated_data)

    def create_or_update(self, instance, validated_data):
        """Create or update a NotificationProfile with notification_delivery_methods."""
        notification_delivery_methods = validated_data.pop('notification_delivery_methods', None)

        if instance is None:
            # Create new instance
            instance = NotificationProfile.objects.create(**validated_data)
        else:
            # Update existing instance using superclass implementation
            instance = super().update(instance, validated_data)

        # Update notification_delivery_methods relationship if provided
        if notification_delivery_methods is not None:
            instance.notification_delivery_methods.set(notification_delivery_methods)

        return instance
