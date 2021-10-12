from typing import cast, Optional

import logging

from django.core import exceptions as django_exceptions
from django.db import transaction
from django.utils import timezone
from django.views import View

from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password

from django_filters import CharFilter, NumberFilter
from django_filters import rest_framework as filters

from rest_framework import permissions, status, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import (
    ParseError, NotAuthenticated, PermissionDenied
)
from rest_framework.request import Request
from rest_framework.response import Response

from ..authentication import AllowBadJwtTokenAuthentication
from ..common.request_helpers import (
    ensure_group_access_level,
    user_and_group_from_request,
)
from ..models import (
    Invitation,
    UserGroupAccessLevel,
)

from ..serializers import InvitationSerializer

from .base_view_set import BaseReadOnlyViewSetMixin
from .atomic_viewsets import (
    AtomicCreateModelMixin, AtomicDestroyModelMixin
)

logger = logging.getLogger(__name__)


class InvitationPermission(permissions.BasePermission):
    def has_object_permission(self, request: Request, view: View, obj: Invitation) -> bool:
        # Unauthenticated users can retrieve invitations by confirmation codes
        # View is an InvitationViewSet which is a GenericViewSet which has the action
        # property
        if getattr(view, 'action') == 'list':
            return True

        try:
            ensure_group_access_level(group=obj.group,
                    min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
                    allow_api_key=False,
                    request=request)
        except NotAuthenticated:
            return False
        except PermissionDenied:
            return False

        return True

class InvitationFilter(filters.FilterSet):
    group__id = NumberFilter()
    invited_user__username = CharFilter()
    invited_by_user__username = CharFilter()
    to_email = CharFilter()

    class Meta:
        model = Invitation
        fields = [
            'group__id', 'invited_user__username', 'invited_by_user__username',
            'to_email'
        ]

class InvitationViewSet(AtomicCreateModelMixin,
        AtomicDestroyModelMixin,
        BaseReadOnlyViewSetMixin):
    lookup_field = 'uuid'
    model_class = Invitation
    authentication_classes = (
        AllowBadJwtTokenAuthentication, SessionAuthentication,
    )
    permission_classes = (InvitationPermission,)
    filterset_class = InvitationFilter
    serializer_class = InvitationSerializer
    search_fields = ('to_email')
    ordering_fields = ('to_email', 'created_at', 'accepted_at')
    ordering = 'created_at'

    def get_queryset(self):
        request = self.request
        is_list = (self.action == 'list')

        # Unauthenticated users can retrieve invitations by confirmation code
        if is_list:
            confirmation_code = request.GET.get('confirmation_code')

            if confirmation_code:
                return Invitation.objects.filter(confirmation_code=confirmation_code)

        user, group = user_and_group_from_request(request=request)

        if user and user.is_superuser:
            return Invitation.objects.all().order_by(self.ordering)

        if (user is None) or user.is_anonymous or (not user.is_active):
            if is_list:
                raise ParseError('confirmation_code is required')

            raise NotAuthenticated()

        if group:
            return Invitation.objects.filter(group=group)

        return Invitation.objects.filter(group__in=user.groups.all())

    @transaction.atomic
    def create(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        invited_user = cast(User, validated_data['invited_user'])

        result = 'created_invitation_for_new_user'
        response_code: int = status.HTTP_201_CREATED

        if (not invited_user.is_active) or invited_user._state.adding:
            if invited_user._state.adding:
                logger.info(f"No existing user {invited_user.username}, creating an invitation and saving inactive user")
                invited_user.save()
            else:
                logger.info(f"Existing inactive user {invited_user.username} exists, creating an invitation")

            saved = serializer.save()
            saved.send_email()
        else:
            result = 'added_access_to_existing_user'
            response_code = status.HTTP_200_OK
            logger.info(f"Found existing user {invited_user.username}, adding group access")
            group = cast(Group, validated_data['group'])
            invited_user.groups.add(group)

            access_level = cast(Optional[int], validated_data.get('group_access_level'))

            if access_level is None:
                logger.info(f'No access level found for {invited_user.username=}')
            else:
                ugal, created = UserGroupAccessLevel.objects.get_or_create(
                        user=invited_user, group=group,
                        defaults={'access_level': access_level})

                if created:
                    logger.info(f"Created new UserGroupAccessLevel for {invited_user.username=}")
                else:
                    if ugal.access_level < access_level:
                        logger.info('Upgrading access level from {ugal.access_level} to {access_level}')
                        ugal.access_level = access_level
                        ugal.save()
                    else:
                        logger.info('Not downgrading access level from {ugal.access_level} to {access_level}')

            # TODO: maybe send mail indicating access is upgraded

        return Response(data={
            'result': result
        }, status=response_code)

    @transaction.atomic
    @action(methods=['POST'], detail=False, authentication_classes=[])
    def accept(self, request: Request):
        logger.info("accepting invitation")

        confirmation_code = request.data['confirmation_code']

        invitation = Invitation.objects.filter(confirmation_code=confirmation_code).first()

        if not invitation:
            logger.warning("Can't find invitation")
            return Response(status=status.HTTP_404_NOT_FOUND)

        if invitation.accepted_at:
            logger.info('Invitation was already accepted')
            return Response(status=status.HTTP_200_OK)

        invited_user = invitation.invited_user

        if not invited_user:
            logger.warning("Can't find invited user")
            return Response(status=status.HTTP_404_NOT_FOUND)

        password = request.data['password']

        try:
            validate_password(password, invited_user)
        except django_exceptions.ValidationError as e:
            serializer_error = serializers.as_serializer_error(e)
            raise serializers.ValidationError(
                {"password": serializer_error["non_field_errors"]}
            )

        now = timezone.now()
        invited_user.set_password(password)
        invited_user.is_active = True
        invited_user.date_joined = now
        invited_user.save()

        group = invitation.group

        if group:
            invited_user.groups.add(group)
            access_level = invitation.group_access_level
            if access_level:
                ugal = invited_user.group_access_levels.filter(group=group).first()

                if ugal:
                    if ugal.access_level < access_level:
                        ugal.access_level = access_level
                        ugal.save()
                else:
                    ugal = UserGroupAccessLevel(user=invited_user, group=group,
                            access_level=access_level)
                    ugal.save()

        else:
            logger.warning('Invitation group not found')

        invitation.accepted_at = now
        invitation.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
