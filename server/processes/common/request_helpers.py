from typing import (
    cast, Any, Dict, Optional, Sequence, Tuple, Union, TYPE_CHECKING
)

import logging
from urllib.parse import urlparse

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest
from django.test.client import RequestFactory

from django.contrib.auth.models import Group, User

from django_middleware_global_request.middleware import get_request

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import (
    ErrorDetail, NotAuthenticated, PermissionDenied
)
from rest_framework.request import (
    Request, ForcedAuthentication
)
from rest_framework import serializers

from ..exception import UnprocessableEntity

if TYPE_CHECKING:
    from ..models import RunEnvironment, SaasToken

logger = logging.getLogger(__name__)


def request_for_context(request: Optional[Union[HttpRequest, Request]] = None) -> Request:
    wsgi_request: Optional[WSGIRequest] = None

    if request is None:
        request = get_request()

    if isinstance(request, Request):
        return request

    if isinstance(request, WSGIRequest):
        wsgi_request = cast(WSGIRequest, request)

    if wsgi_request:
        authenticators: Optional[Sequence[BaseAuthentication]] = None

        if wsgi_request.user:
            auth = getattr(wsgi_request, 'auth')
            logger.info(f"request_for_context(): Found {wsgi_request.user=}, {auth=}")
            authenticators = [cast(BaseAuthentication,
                    ForcedAuthentication(wsgi_request.user, auth)),]

        api_request = Request(wsgi_request, authenticators=authenticators)

        logger.debug(f"request_for_context() set api_request auth: {api_request.user=}, {api_request.auth=}")
        logger.debug(f"request_for_context() set api_request internal auth: {api_request._user=}, {api_request._auth=}")

        return api_request

    logger.info("Can't get request globally, using request factory")
    return make_fake_request()


def make_fake_request(**kwargs) -> Request:
    rf = RequestFactory()

    external_base_url = settings.EXTERNAL_BASE_URL
    parsed = urlparse(external_base_url)
    is_request_secure = parsed.scheme == 'https'
    server_hostname = parsed.hostname
    server_port = str(parsed.port or (443 if is_request_secure else 80))

    logger.debug(f"make_fake_request(): {external_base_url=}, {server_hostname=}")

    return Request(rf.get('/', secure=is_request_secure,
            SERVER_NAME=server_hostname, SERVER_PORT=server_port), **kwargs)


def context_with_request() -> Dict[str, Any]:
    return {
        'request': request_for_context()
    }

def user_and_group_from_request(request: Request = None) -> \
        Tuple[Optional[User], Optional[Group]]:
    r = request or request_for_context()

    user: Optional[User] = None

    # r.user might be an AnonymousUser
    if isinstance(r.user, User):
        user = cast(User, r.user)

    group: Optional[Group] = None

    if r.auth and hasattr(r.auth, 'group'):
        group = cast(Optional[Group], getattr(r.auth, 'group'))

    # For compatibility with existing code that requires a single group for a request.
    # For users with multiple groups, the group is None
    if (not group) and user:
        all_groups = list(user.groups.all())
        if len(all_groups) == 1:
            group = all_groups[0]

    return (user, group)

def required_user_and_group_from_request(request: Optional[Request] = None) -> \
        Tuple[User, Optional[Group]]:
    opt_user, opt_group = user_and_group_from_request(request=request)

    if not opt_user:
        raise NotAuthenticated('No User found')

    if opt_user.is_anonymous:
        raise NotAuthenticated('Anonymous User not allowed')

    if not opt_user.is_active:
        raise PermissionDenied('User not active')

    return (opt_user, opt_group)

def find_group_by_id_or_name(obj_dict: Optional[Dict[str, Any]],
      raise_exception_if_missing=True, check_conflict=True) -> Optional[Group]:
    if obj_dict is None:
        if raise_exception_if_missing:
            raise serializers.ValidationError({
                'group': ['No Group was specified']
            })

        return None

    id = obj_dict.get('id')
    name = obj_dict.get('name')

    if id is not None:
        group = Group.objects.get(pk=id)

        if check_conflict and (name is not None) and (group.name != name):
            raise serializers.ValidationError({
                'name': [ErrorDetail(f"{group.pk=} is named '{group.name}', not '{name}'", code='conflict')]
            })
    else:
        if name is None:
            raise serializers.ValidationError({
                'id': [ErrorDetail('Neither ID or name of Group found in request', code='invalid')]
            })

        group = Group.objects.get(name=name)

    return group

def extract_filtered_group(request: Request,
        request_group: Optional[Group],
        required: bool = True,
        parameter_name: str = 'group__id') -> Optional[Group]:
    group_id = request.GET.get(parameter_name)

    group = request_group
    if request_group is None:
        if group_id is None:
            if required:
                raise serializers.ValidationError(detail='Group ID must be specified')
        else:
            group = Group.objects.filter(id=int(group_id)).first()

            if group is None:
                raise serializers.ValidationError(detail=f'Group {id} not found')
    elif (group_id is not None) and (str(request_group.pk) != group_id):
        raise UnprocessableEntity(detail='Group ID does not match authenticated Group')

    return group

def ensure_group_access_level(group: Optional[Group],
        min_access_level: Optional[int] = -1,
        run_environment: 'Optional[RunEnvironment]' = None,
        allow_api_key: bool = True,
        request: Optional[Request] = None) -> Tuple[User, Optional[Group], int]:
    from ..models import UserGroupAccessLevel

    request = request or request_for_context()
    request_user, request_group = required_user_and_group_from_request(
            request=request)

    if request_user.is_superuser:
        return (request_user, group or request_group,
                UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    if request_group and (request_group != group):
        raise PermissionDenied('Non-matching Group')

    group = group or request_group

    if group is None:
        raise NotAuthenticated('Group required')

    if min_access_level == -1:
        min_access_level = UserGroupAccessLevel.ACCESS_LEVEL_ADMIN
    elif min_access_level is None:
        min_access_level = UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER

    access_level = UserGroupAccessLevel.access_level_for_user_in_group(
      user=request_user, group=group)

    if access_level is None:
        raise PermissionDenied('User has no access to Group')

    if access_level < min_access_level:
        raise PermissionDenied('Insufficient Group access level')

    if request.auth:
        if not allow_api_key:
            ensure_api_key_not_used(request)

        if hasattr(request.auth, 'access_level'):
            token_access_level = cast('SaasToken', request.auth).access_level or \
                    UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER
            if token_access_level < min_access_level:
                raise PermissionDenied('Insufficient Group access level')

            access_level = min(access_level, token_access_level)

        token_run_environment = extract_authenticated_run_environment(
                request=request)

        if (token_run_environment is not None) and \
                (run_environment != token_run_environment):

            logger.warning(f"{token_run_environment=} != {run_environment=}")
            # API Key is scoped to a specific, non-matching Run Environment
            raise PermissionDenied('Invalid Run Environment')

    return (request_user, request_group, access_level)

def extract_authenticated_run_environment(
        request: Optional[Request] = None) -> 'Optional[RunEnvironment]':
    request = request or request_for_context()
    if hasattr(request.auth, 'run_environment'):
        return cast('SaasToken', request.auth).run_environment

    return None

def ensure_api_key_not_used(request: Optional[Request] = None) -> None:
    request = request or request_for_context()

    if type(request.auth).__name__ == 'SaasToken':
        raise PermissionDenied('An API Key cannot be used for this request')
