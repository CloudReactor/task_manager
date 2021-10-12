from datetime import datetime
from typing import cast, Any, List, Dict, Optional

import pytest
from pytest_factoryboy import register

from django.conf import settings
from django.contrib.auth.models import User, Group

from rest_framework.authentication import BaseAuthentication
from rest_framework.request import (
    Request, ForcedAuthentication
)
from rest_framework.response import Response
from rest_framework.test import APIClient

from rest_framework_simplejwt.tokens import RefreshToken

from processes.common.request_helpers import make_fake_request
from processes.models import (
    RunEnvironment, SaasToken, UserGroupAccessLevel
)

from tests.factories import (
    GroupFactory,
    GroupInfoFactory,
    UserFactory,
    SubscriptionPlanFactory,
    SubscriptionFactory,
    RunEnvironmentFactory,
    TaskFactory,
    UnknownExecutionMethodTaskFactory,
    TaskExecutionFactory,
    WorkflowFactory,
    WorkflowTaskInstanceFactory,
    WorkflowTransitionFactory,
    WorkflowExecutionFactory,
    PagerDutyProfileFactory,
    EmailNotificationProfileFactory,
    AlertMethodFactory
)

SEND_ID_NONE = 'none'
SEND_ID_CORRECT = 'correct'
SEND_ID_WRONG = 'wrong'
SEND_ID_NOT_FOUND = 'not found'
SEND_ID_IN_WRONG_GROUP = 'in_wrong_group'
SEND_ID_WITH_OTHER_RUN_ENVIRONMENT = 'in_other_run_environment'
SEND_ID_WITHOUT_RUN_ENVIRONMENT = 'without_run_environment'
SEND_ID_OTHER = 'other'

SCOPE_TYPE_NONE = 'none'
SCOPE_TYPE_CORRECT = 'correct'
SCOPE_TYPE_OTHER = 'other'

CHANGE_ALL = '*'


register(GroupFactory)
register(GroupInfoFactory)
register(UserFactory)
register(SubscriptionPlanFactory)
register(SubscriptionFactory)
register(RunEnvironmentFactory)
register(TaskFactory)
register(UnknownExecutionMethodTaskFactory)
register(TaskExecutionFactory)
register(WorkflowFactory)
register(WorkflowTaskInstanceFactory)
register(WorkflowTransitionFactory)
register(WorkflowExecutionFactory)
register(PagerDutyProfileFactory)
register(EmailNotificationProfileFactory)
register(AlertMethodFactory)


@pytest.fixture
def api_client():
    return APIClient()

def make_saas_token_api_client(user: User, group: Group,
        api_client: APIClient, access_level: Optional[int] = None,
        run_environment: Optional[RunEnvironment] = None) -> APIClient:
    print(f"make_saas_token_api_client() {group=}, {run_environment=}, {access_level=}")

    token, _ = SaasToken.objects.get_or_create(user=user, group=group,
          access_level=access_level or UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
          run_environment=run_environment)
    api_client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
    return api_client

def make_jwt_token_api_client(user: User, api_client: APIClient) -> APIClient:
    header = cast(List[str], settings.SIMPLE_JWT['AUTH_HEADER_TYPES'])[0]
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'{header} {refresh.access_token}')
    return api_client

def make_api_client_from_options(api_client: APIClient,
        is_authenticated: bool = False,
        user: Optional[User] = None, group: Optional[Group] = None,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> APIClient:
    if not is_authenticated:
        return api_client

    if user is None:
        raise RuntimeError('No user')

    if api_key_access_level is None:
        assert(api_key_run_environment is None)
        return make_jwt_token_api_client(user=user, api_client=api_client)

    if group is None:
        raise RuntimeError('No group')

    return make_saas_token_api_client(user=user, group=group,
            api_client=api_client, access_level=api_key_access_level,
            run_environment=api_key_run_environment)

def set_group_access_level(user: User, group: Group,
        access_level: Optional[int]) -> None:
    if access_level is None:
        UserGroupAccessLevel.objects.filter(user=user, group=group).delete()
        user.groups.remove(group)
    else:
        ugal, _created = UserGroupAccessLevel.objects.get_or_create(
                user=user, group=group, defaults={'access_level': access_level})
        ugal.access_level = access_level
        ugal.save()
        user.groups.add(group)

def authenticated_request_for_context(user: User,
        group: Optional[Group],
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None,
        path: Optional[str] = None,  **kwargs) -> Request:
    if api_key_access_level is None:
        assert api_key_run_environment is None
        auth = RefreshToken.for_user(user)
    else:
        assert group is not None
        auth = SaasToken(user=user, group=group,
                run_environment=api_key_run_environment,
                access_level=api_key_access_level)

    authenticators = [cast(BaseAuthentication,
          ForcedAuthentication(user, auth)),]

    print(f"Making fake request with auth {type(auth).__name__}")
    return make_fake_request(authenticators=authenticators, **kwargs)

def context_with_authenticated_request(**kwargs) -> Dict[str, Any]:
    return {
        'request': authenticated_request_for_context(**kwargs)
    }

def check_validation_error(response: Response,
        validation_error_attribute: Optional[str] = None,
        error_code: Optional[str] = None) -> None:
    if validation_error_attribute:
        response_dict = cast(Dict[str, Any], response.data)
        assert(validation_error_attribute in response_dict)

        if error_code:
            assert(response_dict[validation_error_attribute][0].code == error_code)

def iso8601_with_z(dt: Optional[datetime]) -> Optional[str]:
    if dt:
        return dt.isoformat().replace('+00:00', 'Z')

    return None
