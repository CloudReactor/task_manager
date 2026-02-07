from typing import Any, List, Optional, cast

import uuid
from urllib.parse import quote

from django.contrib.auth.models import User
from django.utils import timezone

from processes.models import (
    Event,
    BasicEvent,
    TaskExecution,
    TaskExecutionStatusChangeEvent,
    WorkflowExecution,
    WorkflowExecutionStatusChangeEvent,
    MissingHeartbeatDetectionEvent,
    MissingScheduledTaskExecutionEvent,
    MissingScheduledWorkflowExecutionEvent,
    InsufficientServiceTaskExecutionsEvent,
    DelayedTaskExecutionStartEvent,
    RunEnvironment,
    UserGroupAccessLevel
)

import pytest

from rest_framework.test import APIClient

from conftest import *


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level, api_key_scope_type,
  user_has_another_group, send_group_id_type,
  status_code, expected_indices
""", [
  # Admin with Admin API key, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_CORRECT,
   200, [0, 1, 2]),

  # Admin with Admin API key, no explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_NONE,
   200, [0, 1, 2]),

  # Observer with JWT token, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   False, SEND_ID_CORRECT,
   200, [0, 1, 2]),

  # Observer in single group with JWT token, no explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   False, SEND_ID_NONE,
   200, [0, 1, 2]),

  # Admin in multiple groups with JWT token, no explicit group yields 400
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   True, SEND_ID_NONE,
   400, None),

  # Developer in multiple groups with JWT token, explicit group yields 200
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None, None,
   True, SEND_ID_CORRECT,
   200, [0, 1, 2]),

  # Admin with Observer API key, explicit group succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   False, SEND_ID_CORRECT,
   200, [0, 1, 2]),

  # Admin with multiple groups with Observer API key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   True, SEND_ID_CORRECT,
   200, [0, 1, 2]),

  # No API key with no explicit group in request yields 400
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   None, None,
   True, SEND_ID_NONE,
   400, None),

  # API key with no explicit group in request succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER, None,
   True, SEND_ID_NONE,
   200, [0, 1, 2]),

  # Admin with Admin API key, explicit wrong group yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_WRONG,
   422, None),

  # Admin using JWT, explicit wrong group yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   False, SEND_ID_WRONG,
   422, None),

  # Admin using Admin API key, explicit bad group ID yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN, None,
   False, SEND_ID_NOT_FOUND,
   422, None),

  # Admin using JWT, explicit bad group ID yields 422
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   False, SEND_ID_NOT_FOUND,
   422, None),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None, None,
   False, SEND_ID_CORRECT,
   401, None),
])
def test_event_list(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int], api_key_scope_type: str,
        user_has_another_group: bool, send_group_id_type: str,
        status_code: int, expected_indices: List[int],
        user_factory, group_factory,
        basic_event_factory,
        task_execution_status_change_event_factory,
        insufficient_service_task_executions_event_factory,
        api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    another_group = group_factory()

    if user_has_another_group:
        set_group_access_level(user=user, group=another_group,
                access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

    event_group = group

    events = [
        basic_event_factory(created_by_group=event_group),
        task_execution_status_change_event_factory(created_by_group=event_group),
        insufficient_service_task_executions_event_factory(created_by_group=event_group)
    ]

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=None)

    params = {}

    group_id: Optional[str] = None

    if send_group_id_type == SEND_ID_CORRECT:
        group_id = str(group.id)
    elif send_group_id_type == SEND_ID_NOT_FOUND:
        group_id = '666'
    elif send_group_id_type == SEND_ID_WRONG:
        group_id = str(another_group.id)

    if group_id:
        params['created_by_group__id'] = group_id

    response = client.get('/api/v1/events/', params)

    assert response.status_code == status_code

    if status_code == 200:
        assert group_access_level is not None
        page = response.data
        assert page['count'] == len(expected_indices)
        results = page['results']

        # Build a map of returned UUIDs for comparison
        returned_uuids = {r['uuid'] for r in results}
        expected_uuids = {str(events[i].uuid) for i in expected_indices}

        assert returned_uuids == expected_uuids

        # Verify each event by matching UUID
        for response_event in results:
            # Find the matching event by UUID
            target_event = next(e for e in events if str(e.uuid) == response_event['uuid'])
            ensure_serialized_event_valid(response_event,
                    event=target_event, user=user,
                    group_access_level=group_access_level,
                    api_key_access_level=api_key_access_level,
                    api_key_run_environment=None)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level,
  uuid_send_type,
  status_code
""", [
  # Admin with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   SEND_ID_CORRECT,
   200),

  # Observer with API Key succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   SEND_ID_CORRECT,
   200),

  # Developer with JWT succeeds
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None,
   SEND_ID_CORRECT,
   200),

  # Developer with wrong UUID yields 404
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   None,
   SEND_ID_NOT_FOUND,
   404),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None,
   SEND_ID_CORRECT,
   401),
])
def test_event_fetch(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        uuid_send_type: str,
        status_code: int,
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    event = basic_event_factory(created_by_group=group)

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=None)

    uuid_to_send = uuid.uuid4()

    if uuid_send_type == SEND_ID_CORRECT:
        uuid_to_send = event.uuid

    url = f'/api/v1/events/{uuid_to_send}/'

    response = client.get(url)

    assert response.status_code == status_code

    if status_code == 200:
        ensure_serialized_event_valid(response.data, event=event,
                user=user, group_access_level=group_access_level,
                api_key_access_level=api_key_access_level)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level,
  request_uuid_type, event_type,
  status_code, validation_error_attribute, error_code
""", [
  # Developer with API Key can create basic event
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   SEND_ID_NONE, 'basic_event',
   201, None, None),

  # Admin with JWT can create basic event
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None,
   SEND_ID_NONE, 'basic_event',
   201, None, None),

  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None,
   SEND_ID_NOT_FOUND, 'basic_event',
   400, 'uuid', None),

  # Developer can create task execution status change event
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   SEND_ID_NONE, 'task_execution_status_change_event',
   201, None, None),

  # Developer can create workflow execution status change event
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   SEND_ID_NONE, 'workflow_execution_status_change_event',
   201, None, None),

  # Developer can create insufficient service task executions event
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   SEND_ID_NONE, 'insufficient_service_task_executions_event',
   201, None, None),

  # Observer cannot create events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   SEND_ID_NONE, 'basic_event',
   403, None, None),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None,
   SEND_ID_NONE, 'basic_event',
   401, None, None),
])
def test_event_create_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        request_uuid_type: str, event_type: str,
        status_code: int, validation_error_attribute: Optional[str],
        error_code: Optional[str],
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory,
        workflow_factory, workflow_execution_factory,
        api_client) -> None:
    """
    This tests access control for Event CREATE endpoint.
    """

    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    run_environment = run_environment_factory(created_by_group=group)

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=None)

    request_data = {
        'event_at': timezone.now().isoformat(),
        'severity': 'error',
        'event_type': event_type,
        'error_summary': 'Test event error summary'
    }

    # Add type-specific fields
    if event_type == 'task_execution_status_change_event':
        task = task_factory(created_by_group=group, run_environment=run_environment)
        task_execution = task_execution_factory(task=task)
        request_data['status'] = TaskExecution.Status.FAILED.name
        request_data['task'] = {
            'uuid': str(task.uuid)
        }
        request_data['task_execution'] = {
            'uuid': str(task_execution.uuid)
        }
    elif event_type == 'workflow_execution_status_change_event':
        workflow = workflow_factory(created_by_group=group, run_environment=run_environment)
        workflow_execution = workflow_execution_factory(workflow=workflow)
        request_data['status'] = WorkflowExecution.Status.TERMINATED_AFTER_TIME_OUT.name
        request_data['workflow'] = {
            'uuid': str(workflow.uuid)
        }
        request_data['workflow_execution'] = {
            'uuid': str(workflow_execution.uuid)
        }
    elif event_type == 'insufficient_service_task_executions_event':
        task = task_factory(created_by_group=group, run_environment=run_environment)
        request_data['task'] = {
            'uuid': str(task.uuid)
        }
        request_data['interval_start_at'] = timezone.now().isoformat()
        request_data['interval_end_at'] = timezone.now().isoformat()
        request_data['detected_concurrency'] = 0
        request_data['required_concurrency'] = 1

    if request_uuid_type != SEND_ID_NONE:
        request_data['uuid'] = str(uuid.uuid4())

    old_count = Event.objects.count()

    response = client.post('/api/v1/events/', data=request_data)

    assert response.status_code == status_code

    new_count = Event.objects.count()

    if status_code == 201:
        assert new_count == old_count + 1

        response_dict = cast(dict[str, Any], response.data)
        event_uuid = response_dict['uuid']
        created_event = Event.objects.get(uuid=event_uuid)

        assert group_access_level is not None
        ensure_serialized_event_valid(response_dict,
                event=created_event, user=user,
                group_access_level=group_access_level,
                api_key_access_level=api_key_access_level)
    else:
        assert new_count == old_count
        if validation_error_attribute:
            check_validation_error(response, validation_error_attribute, error_code)


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level,
  status_code
""", [
  # Admin can update events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   200),

  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None,
   200),

  # Developer can update events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   200),

  # Observer cannot update events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   403),

  # Support can update events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT,
   200),

  # Task can update events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   200),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None,
   401),
])
def test_event_update_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        status_code: int,
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    """
    This tests access control for Event UPDATE endpoint.
    """

    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    event = basic_event_factory(created_by_group=group)
    original_summary = event.error_summary

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=None)

    url = f'/api/v1/events/{event.uuid}/'

    request_data = {
        'error_summary': 'Updated event summary',
        'severity': 'warning'
    }

    response = client.patch(url, data=request_data)

    assert response.status_code == status_code

    event.refresh_from_db()

    if status_code == 200:
        assert event.error_summary == 'Updated event summary'
        assert event.severity == Event.Severity.WARNING.value

        ensure_serialized_event_valid(response.data, event=event,
                user=user, group_access_level=group_access_level,
                api_key_access_level=api_key_access_level)
    else:
        # Event should not have been modified
        assert event.error_summary == original_summary


@pytest.mark.django_db
@pytest.mark.parametrize("""
  is_authenticated, group_access_level,
  api_key_access_level,
  status_code
""", [
  # Admin can delete events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   204),

  # Developer can delete events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
   204),

  # Task can delete events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   UserGroupAccessLevel.ACCESS_LEVEL_TASK,
   204),

  # Observer cannot delete events
  (True, UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
   403),

  # No authentication yields 401
  (False, UserGroupAccessLevel.ACCESS_LEVEL_ADMIN,
   None,
   401),
])
def test_event_delete_access_control(
        is_authenticated: bool, group_access_level: Optional[int],
        api_key_access_level: Optional[int],
        status_code: int,
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    """
    This tests access control for Event DELETE endpoint.
    """

    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=group_access_level)

    event = basic_event_factory(created_by_group=group)
    event_uuid = event.uuid

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=is_authenticated, user=user, group=group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=None)

    url = f'/api/v1/events/{event.uuid}/'

    old_count = Event.objects.count()

    response = client.delete(url)

    assert response.status_code == status_code

    new_count = Event.objects.count()

    if status_code == 204:
        assert new_count == old_count - 1
        assert not Event.objects.filter(uuid=event_uuid).exists()
    else:
        # Event should still exist
        assert new_count == old_count
        assert Event.objects.filter(uuid=event_uuid).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("""
  severity_filter, expected_indices
""", [
  # Filter by single severity - text label
  ('ERROR', [1]),
  ('error', [1]),  # case-insensitive
  ('WARNING', [2]),
  ('INFO', [3]),
  ('DEBUG', [4]),

  # Filter by single severity - numeric value
  ('500', [1]),  # ERROR
  ('400', [2]),  # WARNING
  ('300', [3]),  # INFO
  ('200', [4]),  # DEBUG

  # Filter by multiple severities - text labels
  ('ERROR,WARNING', [1, 2]),
  ('error,warning', [1, 2]),  # case-insensitive
  ('INFO,DEBUG,TRACE', [3, 4, 5]),

  # Filter by multiple severities - numeric values
  ('500,400', [1, 2]),
  ('300,200,100', [3, 4, 5]),

  # Filter by multiple severities - mixed text and numeric
  ('ERROR,400,300', [1, 2, 3]),

  # Filter by CRITICAL
  ('CRITICAL', [0]),
  ('600', [0]),

  # Filter by TRACE
  ('TRACE', [5]),
  ('100', [5]),
])
def test_event_filter_by_severity(
        severity_filter: str,
        expected_indices: List[int],
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    """
    Test filtering events by exact severity or list of severities.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create events with different severities
    events = [
        basic_event_factory(created_by_group=group, severity=Event.Severity.CRITICAL.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.ERROR.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.WARNING.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.INFO.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.DEBUG.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.TRACE.value),
    ]

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    params = {
        'severity': severity_filter
    }

    response = client.get('/api/v1/events/', params)

    assert response.status_code == 200

    page = response.data
    assert page['count'] == len(expected_indices)
    results = page['results']

    # Build a map of returned UUIDs for comparison
    returned_uuids = {r['uuid'] for r in results}
    expected_uuids = {str(events[i].uuid) for i in expected_indices}

    assert returned_uuids == expected_uuids


@pytest.mark.django_db
@pytest.mark.parametrize("""
  min_severity_filter, expected_indices
""", [
  # Filter by minimum severity - text labels
  ('CRITICAL', [0]),
  ('critical', [0]),  # case-insensitive
  ('ERROR', [0, 1]),
  ('error', [0, 1]),  # case-insensitive
  ('WARNING', [0, 1, 2]),
  ('INFO', [0, 1, 2, 3]),
  ('DEBUG', [0, 1, 2, 3, 4]),
  ('TRACE', [0, 1, 2, 3, 4, 5]),

  # Filter by minimum severity - numeric values
  ('600', [0]),  # CRITICAL
  ('500', [0, 1]),  # ERROR
  ('400', [0, 1, 2]),  # WARNING
  ('300', [0, 1, 2, 3]),  # INFO
  ('200', [0, 1, 2, 3, 4]),  # DEBUG
  ('100', [0, 1, 2, 3, 4, 5]),  # TRACE
])
def test_event_filter_by_min_severity(
        min_severity_filter: str,
        expected_indices: List[int],
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    """
    Test filtering events by minimum severity.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create events with different severities
    events = [
        basic_event_factory(created_by_group=group, severity=Event.Severity.CRITICAL.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.ERROR.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.WARNING.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.INFO.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.DEBUG.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.TRACE.value),
    ]

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    params = {
        'min_severity': min_severity_filter
    }

    response = client.get('/api/v1/events/', params)

    assert response.status_code == 200

    page = response.data
    assert page['count'] == len(expected_indices)
    results = page['results']

    # Build a map of returned UUIDs for comparison
    returned_uuids = {r['uuid'] for r in results}
    expected_uuids = {str(events[i].uuid) for i in expected_indices}

    assert returned_uuids == expected_uuids


@pytest.mark.django_db
def test_event_filter_by_event_type_single(
    user_factory, group_factory,
    basic_event_factory,
    task_execution_status_change_event_factory,
    missing_heartbeat_detection_event_factory,
    delayed_task_execution_start_event_factory,
    api_client) -> None:
    """
    Test filtering events by a single event_type string.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create events of different types
    events = [
        basic_event_factory(created_by_group=group),
        task_execution_status_change_event_factory(created_by_group=group),
        missing_heartbeat_detection_event_factory(created_by_group=group),
        delayed_task_execution_start_event_factory(created_by_group=group),
    ]

    client = make_api_client_from_options(api_client=api_client,
        is_authenticated=True, user=user, group=group,
        api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        api_key_run_environment=None)

    # Filter by basic_event
    params = {'event_type': 'basic'}
    response = client.get('/api/v1/events/', params)
    assert response.status_code == 200
    page = response.data
    assert page['count'] == 1
    results = page['results']
    assert results[0]['uuid'] == str(events[0].uuid)
    
    # Filter by delayed_task_execution_start
    params = {'event_type': 'delayed_task_execution_start'}
    response = client.get('/api/v1/events/', params)
    assert response.status_code == 200
    page = response.data
    assert page['count'] == 1
    results = page['results']
    assert results[0]['uuid'] == str(events[3].uuid)


@pytest.mark.django_db
def test_event_filter_by_event_type_multiple(
    user_factory, group_factory,
    basic_event_factory,
    task_execution_status_change_event_factory,
    missing_heartbeat_detection_event_factory,
    delayed_task_execution_start_event_factory,
    api_client) -> None:
    """
    Test filtering events by multiple comma-separated event_type strings.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
        access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create events of different types
    events = [
    basic_event_factory(created_by_group=group),
    task_execution_status_change_event_factory(created_by_group=group),
    missing_heartbeat_detection_event_factory(created_by_group=group),
    delayed_task_execution_start_event_factory(created_by_group=group),
    ]

    client = make_api_client_from_options(api_client=api_client,
        is_authenticated=True, user=user, group=group,
        api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        api_key_run_environment=None)

    # Filter by basic_event and task_execution_status_change_event
    params = {'event_type': 'basic,task_execution_status_change'}
    response = client.get('/api/v1/events/', params)
    assert response.status_code == 200
    page = response.data
    assert page['count'] == 2
    results = page['results']

    returned_uuids = {r['uuid'] for r in results}
    expected_uuids = {str(events[0].uuid), str(events[1].uuid)}
    assert returned_uuids == expected_uuids
    
    # Filter by delayed_task_execution_start and missing_heartbeat_detection
    params = {'event_type': 'delayed_task_execution_start,missing_heartbeat_detection'}
    response = client.get('/api/v1/events/', params)
    assert response.status_code == 200
    page = response.data
    assert page['count'] == 2
    results = page['results']

    returned_uuids = {r['uuid'] for r in results}
    expected_uuids = {str(events[2].uuid), str(events[3].uuid)}
    assert returned_uuids == expected_uuids


@pytest.mark.django_db
@pytest.mark.parametrize("""
  max_severity_filter, expected_indices
""", [
  # Filter by maximum severity - text labels
  ('CRITICAL', [0, 1, 2, 3, 4, 5]),
  ('critical', [0, 1, 2, 3, 4, 5]),  # case-insensitive
  ('ERROR', [1, 2, 3, 4, 5]),
  ('error', [1, 2, 3, 4, 5]),  # case-insensitive
  ('WARNING', [2, 3, 4, 5]),
  ('INFO', [3, 4, 5]),
  ('DEBUG', [4, 5]),
  ('TRACE', [5]),

  # Filter by maximum severity - numeric values
  ('600', [0, 1, 2, 3, 4, 5]),  # CRITICAL
  ('500', [1, 2, 3, 4, 5]),  # ERROR
  ('400', [2, 3, 4, 5]),  # WARNING
  ('300', [3, 4, 5]),  # INFO
  ('200', [4, 5]),  # DEBUG
  ('100', [5]),  # TRACE
])
def test_event_filter_by_max_severity(
        max_severity_filter: str,
        expected_indices: List[int],
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    """
    Test filtering events by maximum severity.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create events with different severities
    events = [
        basic_event_factory(created_by_group=group, severity=Event.Severity.CRITICAL.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.ERROR.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.WARNING.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.INFO.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.DEBUG.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.TRACE.value),
    ]

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    params = {
        'max_severity': max_severity_filter
    }

    response = client.get('/api/v1/events/', params)

    assert response.status_code == 200

    page = response.data
    assert page['count'] == len(expected_indices)
    results = page['results']

    # Build a map of returned UUIDs for comparison
    returned_uuids = {r['uuid'] for r in results}
    expected_uuids = {str(events[i].uuid) for i in expected_indices}

    assert returned_uuids == expected_uuids


@pytest.mark.django_db
@pytest.mark.parametrize("""
  min_severity, max_severity, expected_indices
""", [
  # Combine min and max severity - text labels
  # Note: min_severity is the lower bound (higher numeric value = higher severity)
  # So min=WARNING (400) max=ERROR (500) means severity between 400 and 500
  ('ERROR', 'ERROR', [1]),
  ('WARNING', 'ERROR', [1, 2]),
  ('INFO', 'WARNING', [2, 3]),
  ('TRACE', 'DEBUG', [4, 5]),
  ('warning', 'error', [1, 2]),  # case-insensitive

  # Combine min and max severity - numeric values
  ('500', '500', [1]),
  ('400', '500', [1, 2]),
  ('300', '400', [2, 3]),
  ('100', '200', [4, 5]),

  # Combine min and max severity - mixed text and numeric
  ('400', 'ERROR', [1, 2]),
  ('INFO', '400', [2, 3]),

  # Wide range
  ('TRACE', 'CRITICAL', [0, 1, 2, 3, 4, 5]),
  ('100', '600', [0, 1, 2, 3, 4, 5]),
])
def test_event_filter_by_min_and_max_severity(
        min_severity: str,
        max_severity: str,
        expected_indices: List[int],
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    """
    Test filtering events by both minimum and maximum severity.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create events with different severities
    events = [
        basic_event_factory(created_by_group=group, severity=Event.Severity.CRITICAL.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.ERROR.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.WARNING.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.INFO.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.DEBUG.value),
        basic_event_factory(created_by_group=group, severity=Event.Severity.TRACE.value),
    ]

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    params = {
        'min_severity': min_severity,
        'max_severity': max_severity
    }

    response = client.get('/api/v1/events/', params)

    assert response.status_code == 200

    page = response.data
    assert page['count'] == len(expected_indices)
    results = page['results']

    # Build a map of returned UUIDs for comparison
    returned_uuids = {r['uuid'] for r in results}
    expected_uuids = {str(events[i].uuid) for i in expected_indices}

    assert returned_uuids == expected_uuids


@pytest.mark.django_db
def test_event_filter_by_invalid_severity(
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    """
    Test filtering events with invalid severity values returns empty result.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create some events
    basic_event_factory(created_by_group=group, severity=Event.Severity.ERROR.value)
    basic_event_factory(created_by_group=group, severity=Event.Severity.WARNING.value)

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test with invalid severity labels
    params = {'severity': 'INVALID'}
    response = client.get('/api/v1/events/', params)
    assert response.status_code == 200
    assert response.data['count'] == 0

    # Test with invalid min_severity
    params = {'min_severity': 'INVALID'}
    response = client.get('/api/v1/events/', params)
    assert response.status_code == 200
    assert response.data['count'] == 0

    # Test with invalid max_severity
    params = {'max_severity': 'INVALID'}
    response = client.get('/api/v1/events/', params)
    assert response.status_code == 200
    assert response.data['count'] == 0
