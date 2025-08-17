from typing import Any, Optional, TYPE_CHECKING

from django.views import View

from django.contrib.auth.models import Group

from rest_framework import permissions
from rest_framework.exceptions import APIException, NotFound, PermissionDenied

from rest_framework.request import Request

from .common.request_helpers import ensure_group_access_level
from .models.user_group_access_level import UserGroupAccessLevel

if TYPE_CHECKING:
    from .models.run_environment import RunEnvironment

class IsCreatedByGroup(permissions.BasePermission):
    def has_object_permission(self, request: Request, view: View, obj: Any) -> bool:
        """
        Object-level permission to only allow users in the same group to view/edit/delete.
        """

        group = self.group_for_object(obj)
        run_environment = self.run_environment_for_object(obj)
        min_access_level = self.required_access_level(request=request,
                view=view, obj=obj)
        allow_api_key = self.is_api_key_allowed(request=request, view=view,
                obj=obj)

        try:
            ensure_group_access_level(
                  group=group,
                  min_access_level=min_access_level,
                  run_environment=run_environment,
                  allow_api_key=allow_api_key,
                  request=request)
            return True
        except PermissionDenied as pd:
            read_access_level = self.required_access_level_for_read(
                    request=request, view=view, obj=obj)

            if (read_access_level is None) or (min_access_level is None) or \
                    (read_access_level > min_access_level):
                return False

            if read_access_level == min_access_level:
                raise NotFound() from pd

            try:
                ensure_group_access_level(
                      group=group,
                      min_access_level=read_access_level,
                      run_environment=run_environment,
                      allow_api_key=allow_api_key,
                      request=request)
            except PermissionDenied as pd:
                # Client has neither read nor write access
                raise NotFound() from pd

            # Client has read access but not write access
            return False

    def group_for_object(self, obj: Any) -> Optional[Group]:
        if hasattr(obj, 'created_by_group'):
            return obj.created_by_group
        elif hasattr(obj, 'group'):
            return obj.group

        raise APIException("Can't determine Group from object")

    def run_environment_for_object(self, obj: Any) -> 'Optional[RunEnvironment]':
        if hasattr(obj, 'run_environment'):
            return obj.run_environment

        return None

    def required_access_level(self, request: Request, view: View, obj: Any) \
            -> Optional[int]:
        if request.method in permissions.SAFE_METHODS:
            return self.required_access_level_for_read(request=request,
                    view=view, obj=obj)

        return self.required_access_level_for_mutation(request=request,
                view=view, obj=obj)

    def required_access_level_for_read(self, request: Request, view: View,
            obj: Any) -> Optional[int]:
        return UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER

    def required_access_level_for_mutation(self, request: Request, view: View,
            obj: Any) -> Optional[int]:
        return UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER

    def is_api_key_allowed(self, request: Request, view: View,
            obj: Any) -> bool:
        return True

#class RunEnvironmentScope(permissions.BasePermission):
