import logging

from django.views import View

from django_filters import BooleanFilter, CharFilter, NumberFilter
from django_filters import rest_framework as filters

from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import (
    NotFound, PermissionDenied,
)
from rest_framework.request import Request

from ..authentication import AllowBadJwtTokenAuthentication
from ..common import ensure_group_access_level
from ..common.request_helpers import (
    request_for_context, required_user_and_group_from_request,
    extract_filtered_group,
)
from ..models import SaasToken, UserGroupAccessLevel
from ..serializers import SaasTokenSerializer

from .base_view_set import BaseViewSet
from .atomic_viewsets import (
    AtomicCreateModelMixin, AtomicUpdateModelMixin, AtomicDestroyModelMixin
)


logger = logging.getLogger(__name__)


class SaasTokenPermission(permissions.BasePermission):
    def has_object_permission(self, request: Request, view: View,
            obj: SaasToken) -> bool:
        # User can't see or manipulate access tokens with higher access than
        # themselves, at least Developer access is required
        min_access_level = max(obj.access_level, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)
        try:
            ensure_group_access_level(group=obj.group,
                    min_access_level=min_access_level,
                    allow_api_key=False, request=request)
        except PermissionDenied as pd:
            # Don't give user a clue that the Token exists
            raise NotFound() from pd

        return True


class SaasTokenFilter(filters.FilterSet):
    key = CharFilter()
    name = CharFilter()
    description = CharFilter()
    group__id = NumberFilter()
    group__name = CharFilter()
    user__username = CharFilter()
    run_environment__uuid = CharFilter()
    access_level = NumberFilter()
    enabled = BooleanFilter()

    class Meta:
        model = SaasToken
        fields = [
           'key', 'name', 'description',
           'group__id', 'group__name', 'user__username',
           'run_environment__uuid',
           'access_level', 'enabled',
        ]


class SaasTokenViewSet(AtomicCreateModelMixin,
        AtomicUpdateModelMixin, AtomicDestroyModelMixin, BaseViewSet):
    model_class = SaasToken
    authentication_classes = (
        AllowBadJwtTokenAuthentication, SessionAuthentication,
    )
    permission_classes = (permissions.IsAuthenticated, SaasTokenPermission,)
    filterset_class = SaasTokenFilter
    serializer_class = SaasTokenSerializer
    search_fields = (
            'key', 'name', 'group__name', 'run_environment__name',
            'description',
    )

    ordering_fields = (
        'name',
        'key',
        'group__name'
        'user__username',
        'run_environment__name',
        'created_at',
        'description',
        'access_level',
        'enabled',
    )
    ordering = 'name'

    def get_queryset(self):
        request = request_for_context(self.request)
        request_user, request_group = required_user_and_group_from_request(request=request)
        is_list = (self.action == 'list')

        group = extract_filtered_group(request=request, request_user=request_user,
            request_group=request_group, required=is_list)

        qs = SaasToken.objects.prefetch_related(
                'run_environment', 'group', 'user').order_by(self.ordering)

        if group:
            try:
                _user, _group, access_level = ensure_group_access_level(group=group,
                        min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                        run_environment=None, allow_api_key=False, request=request)

            except PermissionDenied as pd:
                if is_list:
                    raise pd

                # User is not a member of the Group.
                # Don't give user a clue that the Group exists
                raise NotFound() from pd

            qs = qs.filter(
                group=group,
                # Don't allow a user to see tokens with more access than the user
                access_level__lte=access_level,
            )
        else:
            # Other actions will cause SaasTokenPermission to check if the user has
            # access to the retrieved SaasToken.
            pass

        return qs
