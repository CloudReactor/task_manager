from typing import cast, Optional

import logging

from django.contrib.auth.models import Group

from rest_framework.exceptions import (
    ErrorDetail, NotFound
)

from rest_framework import serializers

from processes.exception import UnprocessableEntity
from processes.models import (

    RunEnvironment
)

from ..common.request_helpers import (
  ensure_group_access_level,
  find_group_by_id_or_name,
  extract_authenticated_run_environment
)

from ..models import (
    UserGroupAccessLevel
)

from .name_and_uuid_serializer import NameAndUuidSerializer
from .group_serializer import GroupSerializer
from .serializer_helpers import SerializerHelpers

logger = logging.getLogger(__name__)


class GroupSettingSerializerMixin(SerializerHelpers, serializers.Serializer):
    created_by_user = serializers.ReadOnlyField(source='created_by_user.username')
    created_by_group = GroupSerializer(read_only=True, include_users=False)
    run_environment = NameAndUuidSerializer(required=False, allow_null=True,
            view_name='run_environments-detail')

    def to_internal_value(self, data):
        group_dict = data.pop('created_by_group', None)
        data_has_run_environment_key = 'run_environment' in data
        run_environment_dict = data.pop('run_environment', None)

        validated = super().to_internal_value(data)

        group: Optional[Group] = None
        authenticated_group = self.get_request_group()
        if group_dict:
            group = find_group_by_id_or_name(obj_dict=group_dict)
        elif self.instance:
            group = self.instance.created_by_group
        else:
            group = authenticated_group

        if group is None:
            raise UnprocessableEntity({
                'created_by_group': ["Missing created_by_group"]
            })

        logger.info(f"Got {group=}")

        if self.instance and self.instance.created_by_group and \
                (self.instance.created_by_group.pk != group.pk):
            raise UnprocessableEntity({
                'created_by_group': ["Can't change Group"]
            })

        if group is None:
            raise serializers.ValidationError({
                'created_by_group': ['No Group was specified']
            })

        authenticated_run_environment = extract_authenticated_run_environment()
        run_environment: Optional[RunEnvironment] = None

        if run_environment_dict:
            logger.info(f"Found {run_environment_dict=}")
            try:
                run_environment = cast(RunEnvironment,
                        RunEnvironment.find_by_uuid_or_name(
                        obj_dict=run_environment_dict,
                        required_group=group))
            except serializers.ValidationError as validation_error:
                self.handle_to_internal_value_exception(validation_error, field_name='run_environment')
            except (RunEnvironment.DoesNotExist, NotFound) as ex:
                raise UnprocessableEntity({
                    'run_environment': [ErrorDetail('Run Environment does not exist', code='not_found')]
                }) from ex
        elif data_has_run_environment_key:
            run_environment = None
        elif self.instance:
            run_environment = self.instance.run_environment
        else:
            run_environment = authenticated_run_environment

        logger.info(f"Computed {run_environment=}")

        if run_environment and authenticated_run_environment and \
            (authenticated_run_environment.pk != run_environment.pk):
            raise UnprocessableEntity({
                'run_environment': [ErrorDetail('Invalid Run Environment', code='invalid')]
            })

        if run_environment and (run_environment.created_by_group.pk != group.pk):
            raise UnprocessableEntity({
                'run_environment': ['Invalid Run Environment']
            })

        ensure_group_access_level(group=group,
                min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                run_environment=run_environment,
                request=self.context.get('request'))

        validated['created_by_group'] = group
        validated['run_environment'] = run_environment

        return validated
