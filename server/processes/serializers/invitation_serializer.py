from typing import Any, Optional

import binascii
import logging
import os

from django.contrib.auth.models import Group, User

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from processes.common.request_helpers import (
    ensure_group_access_level, request_for_context, required_user_and_group_from_request, find_group_by_id_or_name
)
from processes.models import (
    Invitation,
    UserGroupAccessLevel,
)

from .group_serializer import GroupSerializer
from .user_serializer import UserSerializer


logger = logging.getLogger(__name__)


class InvitationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Invitation
        fields = (
            'uuid', 'url', 'to_email',
            'invited_user', 'invited_by_user', 'group',
            'group_access_level', 'accepted_at'
        )

    url = serializers.HyperlinkedIdentityField(
            view_name='invitations-detail',
            lookup_field='uuid'
    )

    invited_user = UserSerializer(required=False, include_groups=False, include_profile=False)
    invited_by_user = UserSerializer(required=False, include_groups=False, include_profile=False)
    group = GroupSerializer(read_only=True, include_users=False)

    def to_internal_value(self, data) -> dict[str, Any]:
        logger.info(f"to_internal_value: {data=}")

        validated = super().to_internal_value(data)

        request = request_for_context()
        user, group = required_user_and_group_from_request(request=request)

        request_body_group: Optional[Group] = None
        request_body_group_dict = data.pop('group', None)

        if request_body_group_dict is None:
            request_body_group = group
        else:
            request_body_group = find_group_by_id_or_name(request_body_group_dict)

        if request_body_group is None:
            raise serializers.ValidationError({
                'group': ['Invitation is missing Group']
            })

        _user, _group, access_level = ensure_group_access_level(
          group=request_body_group,
          min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
          allow_api_key=False, request=request)

        request_body_access_level = data.get('group_access_level',
                UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER)

        # Just in case another role becomes higher than admin, ensure no privilege escalation
        if request_body_access_level > access_level:
            raise PermissionDenied()

        to_email = data.get('to_email')

        if to_email is None:
            raise serializers.ValidationError({
                'to_email': ['Invitation is missing To Email']
            })

        existing_user = User.objects.filter(username=to_email).first()

        if existing_user is None:
            invited_user = User(username=to_email, email=to_email,
                    is_active=False)
        else:
            invited_user = existing_user

        validated.update({
            'group_access_level': request_body_access_level,
            'group': request_body_group,
            'invited_user': invited_user,
            'invited_by_user': user,
        })

        logger.info(f"to_internal_value: {validated=}")

        return validated

    def create(self, validated_data):
        validated_data['confirmation_code'] = binascii.hexlify(os.urandom(15)).decode()
        return Invitation.objects.create(**validated_data)
