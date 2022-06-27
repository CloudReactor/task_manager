from typing import Optional, Tuple

import logging

from django.db import transaction

from django.contrib.auth.models import Group, User

from rest_framework import serializers, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import (
    APIException,
    PermissionDenied
)
from rest_framework.request import Request
from rest_framework.response import Response

from ..authentication import AllowBadJwtTokenAuthentication
from ..common.request_helpers import (
    find_group_by_id_or_name,
    required_user_and_group_from_request,
)
from ..exception import UnprocessableEntity
from ..models import (
    UserGroupAccessLevel,
)

logger = logging.getLogger(__name__)


class GroupMembershipViewSet(viewsets.ViewSet):
    authentication_classes = (
        AllowBadJwtTokenAuthentication, SessionAuthentication,
    )

    @transaction.atomic
    @action(methods=['POST'], detail=False)
    def remove(self, request: Request):
        user, group, request_user, _request_user_access_level = self.validate_user_and_group(request)

        # Don't allow the last admin to be removed.
        if user == request_user:
            admin_count = UserGroupAccessLevel.admin_count(group=group)

            if admin_count <= 1:
                raise UnprocessableEntity({
                        'user': ["Can't reduce the access level of the last Admin User from a Group"]
                })

        UserGroupAccessLevel.objects.filter(group=group, user=user).delete()
        user.groups.remove(group)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(methods=['POST'], detail=False)
    def update_access_level(self, request: Request):
        user, group, request_user, request_user_access_level = self.validate_user_and_group(request)

        access_level = request.data.get('access_level')

        if (user == request_user) and ((access_level is None) or (access_level < UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)):
            admin_count = UserGroupAccessLevel.admin_count(group=group)

            if admin_count <= 1:
                raise UnprocessableEntity({
                        'user': ["Can't remove the last Admin User from a Group"]
                })

        if (access_level is not None) and (access_level > request_user_access_level):
            raise PermissionDenied('Cannot escalate access level')

        ugal = UserGroupAccessLevel.objects.filter(user=user, group=group).first()

        if ugal:
            if access_level is None:
                logger.info(f'Removing UserGroupAccessLevel for {user.username=}, {group.name=}')
                ugal.delete()
            else:
                logger.info(f'Updating UserGroupAccessLevel for {user.username=}, {group.name=} to {access_level=}')
                ugal.access_level = access_level
                ugal.save()
        else:
            user.groups.add(group)
            if access_level is None:
                logger.info(f'No change in minimum access level for {user.username=}, {group.name=}')
            else:
                logger.info(f'Creating UserGroupAccessLevel for {user.username=}, {group.name=}, {access_level=}')
                UserGroupAccessLevel(user=user, group=group, access_level=access_level).save()

        return Response(status=status.HTTP_204_NO_CONTENT)


    def validate_user_and_group(self, request: Request) -> Tuple[User, Group, User, int]:
        request_user, request_group = required_user_and_group_from_request(request)

        data = request.data
        group_dict = data.get('group')

        group: Optional[Group] = None
        if group_dict is None:
            if request_group:
                group = request_group
            else:
                raise serializers.ValidationError({
                      'group': ['Missing group']
                })
        else:
            group = find_group_by_id_or_name(group_dict)
            if not group:
                raise APIException()

        if request_group and (request_group != group):
            raise PermissionDenied('Group mismatch')

        access_level = UserGroupAccessLevel.access_level_for_user_in_group(
            request_user, group)

        if (access_level is None) or \
                (access_level < UserGroupAccessLevel.ACCESS_LEVEL_ADMIN):
            raise PermissionDenied('Group membership operations require admin access')

        user_obj = data.get('user')

        if user_obj is None:
            raise serializers.ValidationError({
                    'user': ['user is required']
            })

        user = User.objects.filter(username=user_obj['username']).first()

        if user is None:
            raise serializers.ValidationError({
                    'user': ['username not found']
            })

        return (user, group, request_user, access_level)
