from typing import cast, Any, Optional

import logging

from django.db import transaction
from django.db.models import F
from django.db.models.query import QuerySet
from django.views import View

from django.contrib.auth.models import Group

from rest_framework import permissions, serializers, status
from rest_framework.exceptions import ErrorDetail
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters import CharFilter, NumberFilter
from django_filters import rest_framework as filters

from ..permissions import IsCreatedByGroup

from ..models import (
    TaskExecution, Task, RunEnvironment, UserGroupAccessLevel
)
from ..serializers import TaskExecutionSerializer

from ..common.request_helpers import (
    ensure_group_access_level,
    extract_filtered_group
)

from .atomic_viewsets import AtomicCreateModelMixin, AtomicUpdateModelMixin, AtomicDestroyModelMixin
from .base_view_set import BaseViewSet

logger = logging.getLogger(__name__)


class TaskExecutionPermission(IsCreatedByGroup):
    def group_for_object(self, obj: Any) -> Optional[Group]:
        task_execution = cast(TaskExecution, obj)
        return task_execution.task.created_by_group

    def run_environment_for_object(self, obj: Any) -> Optional[RunEnvironment]:
        task_execution = cast(TaskExecution, obj)
        return task_execution.task.run_environment

    def required_access_level(self, request: Request, view: View, obj: Any) \
            -> Optional[int]:
        if request.method == 'DELETE':
            return UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER

        return super().required_access_level(request=request, view=view, obj=obj)

    def required_access_level_for_mutation(self, request: Request, view: View,
            obj: Any) -> Optional[int]:
        return UserGroupAccessLevel.ACCESS_LEVEL_TASK


class TaskExecutionFilter(filters.FilterSet):
    task__uuid = CharFilter()
    task__created_by_group__id = NumberFilter()

    class Meta:
        model = TaskExecution
        fields = ['task__uuid', 'task__created_by_group__id']


class TaskExecutionViewSet(AtomicCreateModelMixin, AtomicUpdateModelMixin,
        AtomicDestroyModelMixin, BaseViewSet):
    model_class = TaskExecution
    serializer_class = TaskExecutionSerializer
    lookup_field = 'uuid'
    permission_classes = (permissions.IsAuthenticated, TaskExecutionPermission,)
    filterset_class = TaskExecutionFilter
    search_fields = ('task__name', 'uuid', 'task_version_signature',
                     'task_version_text', 'hostname',
                     'last_status_message', 'api_base_url',)
    ordering_fields = ('uuid', 'task__name',
                       'started_at', 'finished_at', 'duration',
                       'last_heartbeat_at',
                       'status', 'task_version_signature', 'task_version_text',
                       'wrapper_version',
                       'success_count', 'error_count', 'skipped_count',
                       'expected_count', 'last_status_message',
                       'allocated_cpu_units', 'allocated_memory_mb',
                       'current_cpu_units', 'mean_cpu_units', 'max_cpu_units',
                       'current_memory_mb', 'mean_memory_mb', 'max_memory_mb',
                       'failed_attempts', 'timed_out_attempts', 'exit_code',
                       'api_base_url',
                       'aws_ecs_task_definition_arn', 'aws_ecs_task_arn',
                       'aws_ecs_launch_type', 'aws_ecs_cluster_arn',
                       'aws_ecs_execution_role', 'aws_ecs_task_role',
                       'created_at', 'updated_at',)
    ordering = 'started_at'

    def get_queryset(self):
        return super().get_queryset().alias(duration=
                    F('finished_at') - F('started_at')).select_related(
            'task__created_by_group',
            'started_by', 'marked_done_by', 'killed_by',).prefetch_related(
            'workflowtaskinstanceexecution__workflow_execution',
            'workflowtaskinstanceexecution__workflow_task_instance')

    def filter_queryset_by_group(self, qs: QuerySet, group: Group) -> QuerySet:
        return qs.filter(task__created_by_group=group)

    def filter_queryset_by_run_environment(self, qs: QuerySet,
            run_environment: RunEnvironment) -> QuerySet:
        return qs.filter(task__run_environment=run_environment)

    def get_queryset_for_all_groups(self) -> QuerySet:
        return self.model_class.objects.filter(
            task__created_by_group__in=self.request.user.groups.all()
        ).order_by(self.ordering)

    def extract_group(self, request_group: Optional[Group]) -> Optional[Group]:
        task_uuid = self.request.GET.get('task__uuid')

        if task_uuid:
            return Task.objects.get(uuid=task_uuid).created_by_group

        run_environment_uuid = self.request.GET.get('run_environment__uuid')

        if run_environment_uuid:
            return RunEnvironment.objects.get(uuid=run_environment_uuid).created_by_group

        return extract_filtered_group(request=self.request,
            request_group=request_group,
            required=(request_group is None),
            parameter_name='task__created_by_group__id')

    @transaction.atomic
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        logger.info(f"TaskExecution: {validated_data=}")

        requested_task = validated_data.get('task')
        if requested_task is None:
            raise serializers.ValidationError({
                'task': [ErrorDetail('Task is required', code='missing')]
            })

        ensure_group_access_level(group=requested_task.created_by_group,
                min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK,
                run_environment=requested_task.run_environment)

        if not requested_task.can_start_execution():
            return Response(status=status.HTTP_409_CONFLICT)

        saved = serializer.save()

        if saved.status == TaskExecution.Status.MANUALLY_STARTED:
            saved.manually_start()

        headers = self.get_success_headers(serializer.data)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED,
                headers=headers)

    def update(self, request: Request, *args, **kwargs) -> Response:
        # Change the HTTP status code to 409 Conflict if the requested
        # Task Execution status does not match the response Task Execution status.

        response = super().update(request, *args, **kwargs)

        if response.status_code != status.HTTP_200_OK:
            return response

        request_status_name = request.data.get('status')
        if not request_status_name:
            return response

        if request_status_name == TaskExecution.Status.RUNNING.name:
            actual_status_name = response.data['status']
            if actual_status_name != request_status_name:
                setattr(response, 'status_code', status.HTTP_409_CONFLICT)

        return response
