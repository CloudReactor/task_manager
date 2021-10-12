from typing import cast, Any, Dict, Optional

import logging

from django.contrib.auth.models import Group

from rest_framework import serializers
from rest_framework.exceptions import (
    ErrorDetail,
    NotFound,
    ParseError,
    PermissionDenied,
)

from processes.common.request_helpers import (
    request_for_context, required_user_and_group_from_request,
    find_group_by_id_or_name,
    ensure_group_access_level
)

from processes.exception import UnprocessableEntity

from processes.models import (
    RunEnvironment,
    SaasToken
)
from processes.models.user_group_access_level import UserGroupAccessLevel

from .name_and_uuid_serializer import NameAndUuidSerializer
from .serializer_helpers import SerializerHelpers
from .group_serializer import GroupSerializer

logger = logging.getLogger(__name__)


class SaasTokenSerializer(
        serializers.HyperlinkedModelSerializer, SerializerHelpers):
    class Meta:
        model = SaasToken
        fields = [
                'uuid', 'url', 'key', 'name', 'description',
                'access_level', 'enabled', 'user', 'group',
                'run_environment', 'created_at'
        ]

    key = serializers.CharField(read_only=True)
    user = serializers.ReadOnlyField(source='user.username')
    group = GroupSerializer(include_users=False, read_only=True)

    run_environment = NameAndUuidSerializer(
            view_name='run_environments-detail',
            # FIXME
            read_only=True)

    url = serializers.HyperlinkedIdentityField(
            view_name='api_keys-detail',
            lookup_field='uuid'
    )

    def to_internal_value(self, data) -> Dict[str, Any]:
        # Reject user supplied key as it may not be complex enough
        if data.get('key'):
            raise ParseError({
              'key': ['Key must not be specified.']
            })

        group_request_obj = data.pop('group', None)
        run_environment_obj = data.pop('run_environment', None)

        validated = super().to_internal_value(data)

        request = request_for_context()
        user, group = required_user_and_group_from_request(request=request)

        token_group: Optional[Group] = None
        if group_request_obj:
            token_group = find_group_by_id_or_name(group_request_obj)
            if group and (token_group != group):
                raise PermissionDenied()
        else:
            token_group = group

        if not token_group:
            raise serializers.ValidationError({
                'group': ['Token is missing Group']
            })

        run_environment: Optional[RunEnvironment] = None
        if run_environment_obj:
            try:
                run_environment = cast(RunEnvironment,
                        RunEnvironment.find_by_uuid_or_name(
                        obj_dict=run_environment_obj,
                        required_group=token_group))
            except serializers.ValidationError as validation_error:
                self.handle_to_internal_value_exception(validation_error, field_name='run_environment')
            except (RunEnvironment.DoesNotExist, NotFound) as e:
                raise UnprocessableEntity({
                    'run_environment': [ErrorDetail('Run Environment does not exist', code='not_found')]
                }) from e


        _user, _request_group, request_access_level = \
                ensure_group_access_level(
                group=token_group,
                min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                run_environment=run_environment,
                allow_api_key=False,
                request=request)

        token_access_level = validated.get('access_level',
                UserGroupAccessLevel.ACCESS_LEVEL_TASK)

        if token_access_level > request_access_level:
            logger.warning(f'Denied attempt to escalate access level from {request_access_level} to {token_access_level}')
            raise PermissionDenied()

        validated['user'] = user
        validated['group'] = token_group
        validated['run_environment'] = run_environment

        return validated
