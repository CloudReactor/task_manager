import logging

from django.views import View

from django.contrib.auth.models import User

from django_filters import CharFilter
from django_filters import rest_framework as filters

from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import (
    NotFound, PermissionDenied,
)
from rest_framework.request import Request

from ..authentication import AllowBadJwtTokenAuthentication
from ..common.request_helpers import (
    required_user_and_group_from_request,
    ensure_group_access_level,
    extract_filtered_group,
)
from ..models import UserGroupAccessLevel
from ..serializers import UserSerializer

from .base_view_set import BaseReadOnlyViewSetMixin
from .atomic_viewsets import (
        AtomicUpdateModelMixin, AtomicDestroyModelMixin
)

logger = logging.getLogger(__name__)


class UserPermission(permissions.BasePermission):
    def has_object_permission(self, request: Request, view: View,
            obj: User) -> bool:
        request_user, request_group = required_user_and_group_from_request(
            request=request)

        if request_user.is_superuser or (request_user.username == obj.username):
            return True

        if (request.method not in permissions.SAFE_METHODS) or (request_group is None):
            return False

        try:
            _user, _group, _access_level = ensure_group_access_level(group=request_group,
                min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
                run_environment=None, allow_api_key=False, request=request)
        except PermissionDenied:
            return False

        return True


class UserFilter(filters.FilterSet):
    username = CharFilter()

    class Meta:
        model = User
        fields = ['username']


class UserViewSet(AtomicUpdateModelMixin, AtomicDestroyModelMixin,
        BaseReadOnlyViewSetMixin):
    lookup_field = 'username'
    model_class = User
    authentication_classes = (
        AllowBadJwtTokenAuthentication, SessionAuthentication,
    )
    permission_classes = (permissions.IsAuthenticated, UserPermission,)
    filterset_class = UserFilter
    serializer_class = UserSerializer
    search_fields = ('username', 'email')
    ordering_fields = ('username', 'email')
    ordering = 'username'

    #def create(self, request: Request, *args, **kwargs):
    #    raise APIException('Operation not allowed')

    def get_queryset(self):
        request = self.request
        request_user, request_group = required_user_and_group_from_request(request=request)

        if request_user.is_superuser:
            return User.objects.all()

        is_list = (self.action == 'list')

        group = extract_filtered_group(request=request,
            request_group=request_group, required=is_list)

        if group:
            min_access_level = UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT if is_list \
                    else UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER

            try:
                _user, _group, _access_level = ensure_group_access_level(group=group,
                    min_access_level=min_access_level,
                    run_environment=None, allow_api_key=False, request=request)
            except PermissionDenied as pd:
                if is_list:
                    raise pd

                # User is not a member of the Group.
                # Don't give user a clue that the Group exists
                raise NotFound() from pd

            return group.user_set.order_by(self.ordering)

        return User.objects.filter(groups__in=request_user.groups.all()) \
                .order_by(self.ordering)
