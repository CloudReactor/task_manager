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
    RunEnvironment,
    UserGroupAccessLevel
)

from processes.serializers import (
    EventSerializer,
    BasicEventSerializer,
    TaskExecutionStatusChangeEventSerializer,
    WorkflowExecutionStatusChangeEventSerializer,
    MissingHeartbeatDetectionEventSerializer,
    MissingScheduledTaskExecutionEventSerializer,
    MissingScheduledWorkflowExecutionEventSerializer,
    InsufficientServiceTaskExecutionsEventSerializer
)

import pytest

from rest_framework.test import APIClient

from conftest import *


def ensure_serialized_event_valid(response_dict: dict[str, Any],
        event: Event, user: User,
        group_access_level: int,
        api_key_access_level: Optional[int] = None,
        api_key_run_environment: Optional[RunEnvironment] = None) -> None:
    context = context_with_authenticated_request(user=user,
            group=event.created_by_group,
            api_key_access_level=api_key_access_level,
            api_key_run_environment=api_key_run_environment)

    access_level = group_access_level
    if api_key_access_level is not None:
        access_level = min(access_level, api_key_access_level)

    # Use the appropriate serializer based on event type
    if isinstance(event, TaskExecutionStatusChangeEvent):
        serializer_class = TaskExecutionStatusChangeEventSerializer
    elif isinstance(event, WorkflowExecutionStatusChangeEvent):
        serializer_class = WorkflowExecutionStatusChangeEventSerializer
    elif isinstance(event, InsufficientServiceTaskExecutionsEvent):
        serializer_class = InsufficientServiceTaskExecutionsEventSerializer
    elif isinstance(event, MissingHeartbeatDetectionEvent):
        serializer_class = MissingHeartbeatDetectionEventSerializer
    elif isinstance(event, MissingScheduledTaskExecutionEvent):
        serializer_class = MissingScheduledTaskExecutionEventSerializer
    elif isinstance(event, MissingScheduledWorkflowExecutionEvent):
        serializer_class = MissingScheduledWorkflowExecutionEventSerializer
    elif isinstance(event, BasicEvent):
        serializer_class = BasicEventSerializer
    else:
        serializer_class = EventSerializer

    assert response_dict == serializer_class(event, context=context).data


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
def test_event_polymorphic_serialization(
        user_factory, group_factory, run_environment_factory,
        task_factory, task_execution_factory,
        workflow_factory, workflow_execution_factory,
        basic_event_factory,
        task_execution_status_change_event_factory,
        workflow_execution_status_change_event_factory,
        insufficient_service_task_executions_event_factory,
        api_client) -> None:
    """
    Test that the API correctly returns different event types with their specific fields.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create events of different types
    basic_event = basic_event_factory(created_by_group=group)
    task_event = task_execution_status_change_event_factory(created_by_group=group)
    workflow_event = workflow_execution_status_change_event_factory(created_by_group=group)
    insufficient_event = insufficient_service_task_executions_event_factory(created_by_group=group)

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test list endpoint returns correct event types
    response = client.get('/api/v1/events/')
    assert response.status_code == 200

    print(f"response.data: '{response.data}'")

    results = response.data['results']
    assert len(results) == 4

    # Check that each event has correct event_type
    event_types = {r['uuid']: r['event_type'] for r in results}
    assert event_types[str(basic_event.uuid)] == 'basic_event'
    assert event_types[str(task_event.uuid)] == 'task_execution_status_change_event'
    assert event_types[str(workflow_event.uuid)] == 'workflow_execution_status_change_event'
    assert event_types[str(insufficient_event.uuid)] == 'insufficient_service_task_executions_event'

    # Test retrieve endpoint for TaskExecutionStatusChangeEvent
    response = client.get(f'/api/v1/events/{task_event.uuid}/')
    assert response.status_code == 200
    assert response.data['event_type'] == 'task_execution_status_change_event'
    assert 'task' in response.data
    assert 'task_execution' in response.data

    # Test retrieve endpoint for WorkflowExecutionStatusChangeEvent
    response = client.get(f'/api/v1/events/{workflow_event.uuid}/')
    assert response.status_code == 200
    assert response.data['event_type'] == 'workflow_execution_status_change_event'
    assert 'workflow' in response.data
    assert 'workflow_execution' in response.data

    # Test retrieve endpoint for InsufficientServiceTaskExecutionsEvent
    response = client.get(f'/api/v1/events/{insufficient_event.uuid}/')
    assert response.status_code == 200
    assert response.data['event_type'] == 'insufficient_service_task_executions_event'
    assert 'task' in response.data
    assert 'interval_start_at' in response.data
    assert 'interval_end_at' in response.data
    assert 'detected_concurrency' in response.data
    assert 'required_concurrency' in response.data


@pytest.mark.django_db
def test_event_filtering_by_severity(
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    """
    Test that events can be filtered by severity.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create events with different severities
    error_event = basic_event_factory(created_by_group=group, severity=Event.Severity.ERROR.value)
    warning_event = basic_event_factory(created_by_group=group, severity=Event.Severity.WARNING.value)
    info_event = basic_event_factory(created_by_group=group, severity=Event.Severity.INFO.value)

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Filter by ERROR severity
    response = client.get('/api/v1/events/', {'severity': Event.Severity.ERROR.value})
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['uuid'] == str(error_event.uuid)

    # Filter by WARNING severity
    response = client.get('/api/v1/events/', {'severity': Event.Severity.WARNING.value})
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['uuid'] == str(warning_event.uuid)

    # Filter by INFO severity
    response = client.get('/api/v1/events/', {'severity': Event.Severity.INFO.value})
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['uuid'] == str(info_event.uuid)


@pytest.mark.django_db
def test_basic_event_serialization_deserialization(
        user_factory, group_factory,
        basic_event_factory,
        api_client) -> None:
    """
    Test that BasicEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a BasicEvent
    basic_event = basic_event_factory(
        created_by_group=group,
        severity=Event.Severity.INFO.value,
        error_summary="Test basic event summary",
        error_details_message="Test basic event details"
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test retrieve endpoint
    response = client.get(f'/api/v1/events/{basic_event.uuid}/')
    assert response.status_code == 200
    
    # Verify event_type
    assert response.data['event_type'] == 'basic_event'
    
    # Verify basic fields
    assert response.data['uuid'] == str(basic_event.uuid)
    assert response.data['severity'] == 'info'  # Severity is serialized as lowercase string
    assert response.data['error_summary'] == "Test basic event summary"
    assert response.data['error_details_message'] == "Test basic event details"
    
    # Verify serialization matches expected format
    ensure_serialized_event_valid(
        response.data,
        basic_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )


@pytest.mark.django_db
def test_missing_heartbeat_detection_event_serialization_deserialization(
        user_factory, group_factory, task_factory, task_execution_factory,
        api_client) -> None:
    """
    Test that MissingHeartbeatDetectionEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a Task first
    task = task_factory(created_by_group=group)
    task_execution = task_execution_factory(task=task)

    # Create a MissingHeartbeatDetectionEvent manually to avoid factory initialization issues
    from datetime import timedelta
    from django.utils import timezone
    now = timezone.now()
    
    heartbeat_event = MissingHeartbeatDetectionEvent.objects.create(
        created_by_group=group,
        task=task,
        task_execution=task_execution,
        last_heartbeat_at=now - timedelta(minutes=10),
        expected_heartbeat_at=now - timedelta(minutes=5),
        heartbeat_interval_seconds=300,
        severity=Event.Severity.ERROR.value
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test retrieve endpoint
    response = client.get(f'/api/v1/events/{heartbeat_event.uuid}/')
    assert response.status_code == 200
    
    # Verify event_type
    assert response.data['event_type'] == 'missing_heartbeat_detection_event'
    
    # Verify heartbeat-specific fields exist
    assert 'task' in response.data
    assert 'last_heartbeat_at' in response.data
    assert 'expected_heartbeat_at' in response.data
    assert 'heartbeat_interval_seconds' in response.data
    
    # Verify the task reference
    assert response.data['task']['uuid'] == str(task.uuid)
    assert response.data['task']['name'] == task.name
    
    # Verify serialization matches expected format
    ensure_serialized_event_valid(
        response.data,
        heartbeat_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )


@pytest.mark.django_db
def test_missing_scheduled_task_execution_event_serialization_deserialization(
        user_factory, group_factory, task_factory,
        api_client) -> None:
    """
    Test that MissingScheduledTaskExecutionEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a Task first
    task = task_factory(created_by_group=group)

    # Create a MissingScheduledTaskExecutionEvent manually
    from django.utils import timezone
    now = timezone.now()
    
    scheduled_event = MissingScheduledTaskExecutionEvent.objects.create(
        created_by_group=group,
        task=task,
        schedule="0 12 * * *",
        expected_execution_at=now,
        severity=Event.Severity.ERROR.value
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test retrieve endpoint
    response = client.get(f'/api/v1/events/{scheduled_event.uuid}/')
    assert response.status_code == 200
    
    # Verify event_type
    assert response.data['event_type'] == 'missing_scheduled_task_execution_event'
    
    # Verify scheduled task execution-specific fields
    assert 'task' in response.data
    assert 'schedule' in response.data
    assert 'expected_execution_at' in response.data
    
    # Verify the task reference
    assert response.data['task']['uuid'] == str(task.uuid)
    
    # Verify serialization matches expected format
    ensure_serialized_event_valid(
        response.data,
        scheduled_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )


@pytest.mark.django_db
def test_missing_scheduled_workflow_execution_event_serialization_deserialization(
        user_factory, group_factory, workflow_factory,
        api_client) -> None:
    """
    Test that MissingScheduledWorkflowExecutionEvent can be properly serialized and deserialized.
    """
    user = user_factory()
    group = user.groups.first()

    set_group_access_level(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER)

    # Create a Workflow first
    workflow = workflow_factory(created_by_group=group)

    # Create a MissingScheduledWorkflowExecutionEvent manually
    from django.utils import timezone
    now = timezone.now()
    
    workflow_event = MissingScheduledWorkflowExecutionEvent.objects.create(
        created_by_group=group,
        workflow=workflow,
        schedule="0 12 * * *",
        expected_execution_at=now,
        severity=Event.Severity.ERROR.value
    )

    client = make_api_client_from_options(api_client=api_client,
            is_authenticated=True, user=user, group=group,
            api_key_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            api_key_run_environment=None)

    # Test retrieve endpoint
    response = client.get(f'/api/v1/events/{workflow_event.uuid}/')
    assert response.status_code == 200
    
    # Verify event_type
    assert response.data['event_type'] == 'missing_scheduled_workflow_execution_event'
    
    # Verify scheduled workflow execution-specific fields
    assert 'workflow' in response.data
    assert 'schedule' in response.data
    assert 'expected_execution_at' in response.data
    
    # Verify the workflow reference
    assert response.data['workflow']['uuid'] == str(workflow.uuid)
    
    # Verify serialization matches expected format
    ensure_serialized_event_valid(
        response.data,
        workflow_event,
        user,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
        UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER
    )

