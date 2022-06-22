from datetime import datetime
from typing import cast, Any, List, Optional, Tuple

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

from pytest_assert_utils import *

from processes.common.request_helpers import (
    context_with_request, make_fake_request
)
from processes.models import *
from processes.serializers import *

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
    WorkflowTaskInstanceExecutionFactory,
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
register(WorkflowTaskInstanceExecutionFactory)
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

def context_with_authenticated_request(**kwargs) -> dict[str, Any]:
    return {
        'request': authenticated_request_for_context(**kwargs)
    }

def check_validation_error(response: Response,
        validation_error_attribute: Optional[str] = None,
        error_code: Optional[str] = None) -> None:
    if validation_error_attribute:
        response_dict = cast(dict[str, Any], response.data)
        assert(validation_error_attribute in response_dict)

        if error_code:
            assert(response_dict[validation_error_attribute][0].code == error_code)

def iso8601_with_z(dt: Optional[datetime]) -> Optional[str]:
    if dt:
        return dt.isoformat().replace('+00:00', 'Z')

    return None

def split_url(url: str) -> Tuple[Optional[str], str]:
    double_slash_index = url.find('//')
    if double_slash_index >= 0:
        next_slash_index = url.find('/', double_slash_index + 2)

        if next_slash_index >= 0:
            return (url[0:next_slash_index], url[next_slash_index:])

        return (url, '')

    return (None, url)

def verify_name_uuid_url_match(body_1: dict[str, Any],
        body_2: dict[str, Any], check_name: bool = True) -> None:
    assert(body_1['uuid'] == body_2['uuid'])

    if check_name:
        assert(body_1['name'] == body_2['name'])

    url_1 = body_1.get('url')
    url_2 = body_2.get('url')

    if url_1 is None:
        assert url_2 is None
    else:
        assert url_2 is not None

        t_1 = split_url(url_1)
        t_2 = split_url(url_2)

        if (t_1[0] is not None) and (t_2[0] is not None):
            assert t_1[0] == t_2[0]

        assert t_1[1] == t_2[1]

def ensure_attributes_match(body_dict: dict[str, Any], model,
        attrs: list[str]) -> None:
    for attr in attrs:
        x = getattr(model, attr)

        if attr.find('uuid') >= 0:
            x = str(x)
        elif isinstance(x, datetime):
            x = x.isoformat().replace('+00:00', 'Z')

        assert body_dict[attr] == x

EXECUTABLE_ATTRIBUTES = [
    'schedule', 'scheduled_instance_count',
    'max_concurrency',
    'max_age_seconds', 'default_max_retries',
    'enabled',
    'postponed_failure_before_success_seconds',
    'max_postponed_failure_count',
    'max_postponed_timeout_count',
    'min_missing_execution_delay_seconds',
    'postponed_missing_execution_before_start_seconds',
    'max_postponed_missing_execution_count',
    'min_missing_execution_delay_seconds',
    'should_clear_failure_alerts_on_success',
    'should_clear_timeout_alerts_on_success',
]


def validate_serialized_task(body_task: dict[str, Any], model_task: Task,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_task, model_task, [
        'uuid', 'name', 'description', 'dashboard_url',
        'infrastructure_website_url',
        'max_manual_start_delay_before_alert_seconds',
        'max_manual_start_delay_before_abandonment_seconds',
        'heartbeat_interval_seconds',
        'max_heartbeat_lateness_before_alert_seconds',
        'max_heartbeat_lateness_before_abandonment_seconds',
        'is_service', 'service_instance_count',
        'min_service_instance_count',
        'project_url', 'log_query', 'logs_url',
        'was_auto_created', 'passive',
        'created_at', 'updated_at',
    ] + EXECUTABLE_ATTRIBUTES)

    model_emc = model_task.execution_method_capability
    body_emc = body_task['execution_method_capability']
    if model_task.execution_method_capability:
         assert_dict_is_subset(model_emc, body_emc, recursive=True)

    assert body_task['created_by_group'] == GroupSerializer(
            model_task.created_by_group,
            include_users=False, context=context).data

    assert model_task.created_by_user is not None # for mypy

    assert body_task['created_by_user'] == model_task.created_by_user.username

    run_environment_dict = NameAndUuidSerializer(
            model_task.run_environment, context=context,
            view_name='run_environments-detail').data

    verify_name_uuid_url_match(body_task['run_environment'],
            run_environment_dict)

    if model_task.latest_task_execution is None:
        assert body_task['latest_task_execution'] is None

def validate_serialized_task_execution(body_task_execution: dict[str, Any],
        model_task_execution: TaskExecution,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_task_execution, model_task_execution, [
        'uuid', 'dashboard_url', 'infrastructure_website_url',
        'task_version_number', 'task_version_text',
        'task_version_signature', 'commit_url',
        'other_instance_metadata',
        'hostname',
        'environment_variables_overrides',
        'started_at',
        'finished_at',
        'marked_done_at',
        'marked_outdated_at',
        'kill_started_at', 'kill_finished_at',
        'kill_error_code',
        'last_heartbeat_at',
        'failed_attempts', 'timed_out_attempts',
        'exit_code', 'last_status_message',
        'error_count', 'skipped_count',
        'expected_count', 'success_count',
        'other_runtime_metadata',
        'current_cpu_units', 'mean_cpu_units', 'max_cpu_units',
        'current_memory_mb', 'mean_memory_mb', 'max_memory_mb',
        'wrapper_version', 'wrapper_log_level',
        'deployment', 'process_command', 'is_service',
        'task_max_concurrency', 'max_conflicting_age_seconds',
        'prevent_offline_execution',
        'process_timeout_seconds', 'process_termination_grace_period_seconds',
        'process_max_retries', 'process_retry_delay_seconds',
        'schedule',
        'heartbeat_interval_seconds',
        'api_base_url', # Don't expose api_key
        'api_request_timeout_seconds',
        'api_retry_delay_seconds',
        'api_resume_delay_seconds',
        'api_error_timeout_seconds',
        'api_task_execution_creation_error_timeout_seconds',
        'api_task_execution_creation_conflict_timeout_seconds',
        'api_task_execution_creation_conflict_retry_delay_seconds',
        'api_final_update_timeout_seconds',
        'status_update_interval_seconds',
        'status_update_port', 'status_update_message_max_bytes',
        'debug_log_tail', 'error_log_tail',
        'embedded_mode',
        'created_at', 'updated_at',
    ])

    task_dict = NameAndUuidSerializer(
            model_task_execution.task, context=context,
            view_name='tasks-detail').data

    verify_name_uuid_url_match(body_task_execution['task'],
            task_dict)

    assert body_task_execution['status'] == TaskExecution.Status(
            model_task_execution.status).name

    assert body_task_execution['started_by'] == model_task_execution \
            .started_by.username

    if model_task_execution.stop_reason is None:
        assert body_task_execution['stop_reason'] is None
    else:
        body_task_execution['stop_reason'] == TaskExecution.StopReason(
            model_task_execution.stop_reason).name

    if model_task_execution.marked_done_by is None:
        assert body_task_execution['marked_done_by'] is None
    else:
        body_task_execution['marked_done_by'] == model_task_execution \
                .marked_done_by.username

    if model_task_execution.killed_by is None:
        assert body_task_execution['killed_by'] is None
    else:
        body_task_execution['killed_by'] == model_task_execution \
                .killed_by.username

    try:
        wtie = model_task_execution.workflowtaskinstanceexecution
        wtie_dict = NameAndUuidSerializer(wtie, include_name=False,
                context=context).data
        verify_name_uuid_url_match(
                body_task_execution['workflow_task_instance_execution'],
                wtie_dict, check_name=False)
    except WorkflowTaskInstanceExecution.DoesNotExist:
        assert body_task_execution['workflow_task_instance_execution'] is None


def validate_serialized_workflow(body_workflow: dict[str, Any],
        model_workflow: Workflow,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_workflow, model_workflow, [
        'uuid', 'name', 'description', 'dashboard_url',
        'schedule', 'max_concurrency',
        'max_age_seconds', 'default_max_retries',
        'latest_workflow_execution',
        'enabled',
        'created_at', 'updated_at'
    ] + EXECUTABLE_ATTRIBUTES)

    assert body_workflow['created_by_group'] == GroupSerializer(
            model_workflow.created_by_group,
            include_users=False, context=context).data

    assert model_workflow.created_by_user is not None # for mypy

    assert body_workflow['created_by_user'] == model_workflow.created_by_user.username

    run_environment_dict = NameAndUuidSerializer(
            model_workflow.run_environment, context=context,
            view_name='run_environments-detail').data

    verify_name_uuid_url_match(body_workflow['run_environment'],
            run_environment_dict)

    if model_workflow.latest_workflow_execution is None:
        assert body_workflow['latest_workflow_execution'] is None
    else:
        validate_serialized_workflow_execution_summary(
                body_workflow['latest_workflow_execution'],
                model_workflow.latest_workflow_execution,
                context=context)


def validate_serialized_workflow_execution_summary(
        body_workflow_execution: dict[str, Any],
        model_workflow_execution: WorkflowExecution,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    ensure_attributes_match(body_workflow_execution, model_workflow_execution, [
        'uuid', 'dashboard_url',
        'started_at', 'finished_at', 'last_heartbeat_at',
        'stop_reason', 'marked_done_at',
        'kill_started_at', 'kill_finished_at',
        'kill_error_code',
        'failed_attempts', 'timed_out_attempts',
        'created_at', 'updated_at'
    ])

    assert body_workflow_execution['status'] == WorkflowExecution.Status(
            model_workflow_execution.status).name

    assert body_workflow_execution['run_reason'] == WorkflowExecution.RunReason(
            model_workflow_execution.run_reason).name

    if model_workflow_execution.stop_reason is None:
        assert body_workflow_execution['stop_reason'] is None
    else:
        assert body_workflow_execution['stop_reason'] == WorkflowExecution.RunReason(
                model_workflow_execution.stop_reason).name


def validate_serialized_workflow_execution(body_workflow_execution: dict[str, Any],
        model_workflow_execution: WorkflowExecution,
        context: Optional[dict[str, Any]] = None) -> None:
    context = context or context_with_request()

    validate_serialized_workflow_execution_summary(body_workflow_execution,
            model_workflow_execution, context=context)

    workflow_dict = NameAndUuidSerializer(
            model_workflow_execution.workflow, context=context,
            view_name='workflows-detail').data

    verify_name_uuid_url_match(body_workflow_execution['workflow'],
            workflow_dict)

    assert body_workflow_execution['started_by'] == model_workflow_execution \
            .started_by.username

    if model_workflow_execution.marked_done_by is None:
        assert body_workflow_execution['marked_done_by'] is None
    else:
        body_workflow_execution['marked_done_by'] == model_workflow_execution \
                .marked_done_by.username

    if model_workflow_execution.killed_by is None:
        assert body_workflow_execution['killed_by'] is None
    else:
        body_workflow_execution['killed_by'] == model_workflow_execution \
                .killed_by.username
