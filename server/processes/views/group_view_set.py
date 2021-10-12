import logging

from django.views import View

from django.contrib.auth.models import Group

from django_filters import CharFilter, NumberFilter
from django_filters import rest_framework as filters

from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request

from processes.models.user_group_access_level import UserGroupAccessLevel

from ..authentication import AllowBadJwtTokenAuthentication
from ..common.request_helpers import ensure_api_key_not_used, ensure_group_access_level, required_user_and_group_from_request, user_and_group_from_request
from ..serializers import GroupSerializer

from .base_view_set import BaseViewSet
from .atomic_viewsets import (
        AtomicCreateModelMixin, AtomicUpdateModelMixin, AtomicDestroyModelMixin
)

logger = logging.getLogger(__name__)


class GroupPermission(permissions.BasePermission):
    def has_object_permission(self, request: Request, view: View,
            obj: Group) -> bool:
        min_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN
        if request.method in permissions.SAFE_METHODS:
            min_access_level = UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER

        user, group = required_user_and_group_from_request(request=request)

        if group and (group != obj):
            logger.warning("Authenticated Group does not match request Group")
            return False

        access_level = UserGroupAccessLevel.access_level_for_user_in_group(
                user=user, group=obj)

        if access_level is None:
            raise NotFound()

        try:
            ensure_group_access_level(group=obj,
                min_access_level=min_access_level,
                allow_api_key=False,
                request=request)
        except PermissionDenied:
            logger.exception(f'Insufficient permission to access Group {obj.name}')
            return False

        return True


class GroupFilter(filters.FilterSet):
    id = NumberFilter()
    name = CharFilter()

    class Meta:
        model = Group
        fields = ['id', 'name']


class GroupViewSet(BaseViewSet, AtomicCreateModelMixin,
        AtomicUpdateModelMixin, AtomicDestroyModelMixin):
    lookup_field = 'id'
    model_class = Group
    authentication_classes = (
        AllowBadJwtTokenAuthentication, SessionAuthentication,
    )
    permission_classes = (permissions.IsAuthenticated, GroupPermission,)
    filterset_class = GroupFilter
    serializer_class = GroupSerializer
    search_fields = ('id', 'name')
    ordering_fields = ('id', 'name',)
    ordering = 'name'

    def get_queryset(self):
        user, group = user_and_group_from_request()

        if user.is_superuser:
            return Group.objects.all().order_by(self.ordering)

        if group:
            return Group.objects.filter(pk=group.pk)
        else:
            return user.groups.all().order_by(self.ordering)

    def create(self, request: Request, *args, **kwargs):
        ensure_api_key_not_used(request)
        return super().create(request, *args, **kwargs)
