from typing import cast, Any, Optional

import logging

from django.db import transaction
from django.db.models.query import QuerySet
from django.views import View

from django.contrib.auth.models import Group

from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ErrorDetail
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters import CharFilter
from django_filters import rest_framework as filters

from ..models import *
from ..permissions import IsCreatedByGroup
from ..serializers import WorkflowExecutionSerializer, \
    WorkflowExecutionSummarySerializer
from ..common.request_helpers import (
    ensure_group_access_level,
    extract_filtered_group
)

from .atomic_viewsets import (
    AtomicCreateModelMixin,
    AtomicUpdateModelMixin,
    AtomicDestroyModelMixin
)
from .base_view_set import BaseViewSet

logger = logging.getLogger(__name__)


class WorkflowExecutionPermission(IsCreatedByGroup):
    def group_for_object(self, obj: Any) -> Optional[Group]:
        workflow_execution = cast(WorkflowExecution, obj)
        return workflow_execution.workflow.created_by_group

    def run_environment_for_object(self, obj: Any) -> Optional[RunEnvironment]:
        workflow_execution = cast(WorkflowExecution, obj)
        return workflow_execution.workflow.run_environment

    def required_access_level(self, request: Request, view: View, obj: Any) \
            -> Optional[int]:
        if request.method == 'DELETE':
            return UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER

        return super().required_access_level(request=request, view=view, obj=obj)

    def required_access_level_for_mutation(self, request: Request, view: View,
            obj: Any) -> Optional[int]:
        return UserGroupAccessLevel.ACCESS_LEVEL_TASK


class WorkflowExecutionFilter(filters.FilterSet):
    class Meta:
        model = WorkflowExecution
        fields = ['workflow__uuid', 'workflow__created_by_group__id']

    @property
    def qs(self):
        rv = super().qs

        status_list_str = self.request.query_params.get('status__in')

        if status_list_str:
            status_strings = status_list_str.split(',')
            statuses = [WorkflowExecution.Status[s.upper()].value for s in status_strings]
            rv = rv.filter(status__in=statuses)

        return rv


class WorkflowExecutionViewSet(AtomicCreateModelMixin,
        AtomicUpdateModelMixin, AtomicDestroyModelMixin, BaseViewSet):
    model_class = WorkflowExecution
    serializer_class = WorkflowExecutionSerializer
    lookup_field = 'uuid'
    permission_classes = (permissions.IsAuthenticated, WorkflowExecutionPermission,)
    filterset_class = WorkflowExecutionFilter
    search_fields = ('workflow__name', 'uuid',)
    ordering_fields = ('uuid', 'workflow__name',
                       'started_at', 'finished_at',
                       'status', 'run_reason',
                       'failed_attempts', 'timed_out_attempts',
                       'created_at', 'updated_at',)
    ordering = 'started_at'

    def get_queryset(self):
        return super().get_queryset().select_related(
                'workflow__created_by_group', 'workflow__run_environment',
                'started_by', 'marked_done_by', 'killed_by',)

    def filter_queryset_by_group(self, qs: QuerySet, group: Group) -> QuerySet:
        return qs.filter(workflow__created_by_group=group)

    def filter_queryset_by_run_environment(self, qs: QuerySet,
            run_environment: RunEnvironment) -> QuerySet:
        return qs.filter(workflow__run_environment=run_environment)

    def get_queryset_for_all_groups(self) -> QuerySet:
        return self.model_class.objects.filter(
            workflow__created_by_group__in=self.request.user.groups.all()
        ).order_by(self.ordering)

    def extract_group(self, request_group: Optional[Group]):
        workflow_uuid = self.request.GET.get('workflow__uuid')

        if workflow_uuid:
            return Workflow.objects.get(uuid=workflow_uuid).created_by_group

        run_environment_uuid = self.request.GET.get('run_environment__uuid')

        if run_environment_uuid:
            return RunEnvironment.objects.get(uuid=run_environment_uuid).created_by_group

        return extract_filtered_group(request=self.request,
            request_group=request_group,
            required=(request_group is None),
            parameter_name='workflow__created_by_group__id')

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowExecutionSummarySerializer
        else:
            return WorkflowExecutionSerializer

    @transaction.atomic
    @action(methods=['post'], detail=True,
            url_path='workflow_task_instance_executions',
            url_name='workflow_task_instance_executions')
    def start_task_instance_executions(self, request: Request, uuid=None):
        workflow_execution = WorkflowExecution.objects.\
            prefetch_related('workflow').get(uuid=uuid)

        self.check_object_permissions(request, workflow_execution)

        wpti_dicts = request.data['workflow_task_instances']
        wpti_uuids = [x['uuid'] for x in wpti_dicts]

        updated_workflow_execution = workflow_execution.start_task_instance_executions(
            wpti_uuids)
        return self.respond_with_workflow_execution(request, updated_workflow_execution)

    @transaction.atomic
    @action(methods=['post'], detail=True,
            url_path='retry', url_name='retry')
    def retry(self, request: Request, uuid=None):
        workflow_execution = WorkflowExecution.objects.\
            select_related('workflow').get(uuid=uuid)

        self.check_object_permissions(request, workflow_execution)

        updated_workflow_execution = workflow_execution.retry()
        return self.respond_with_workflow_execution(request, updated_workflow_execution)

    @transaction.atomic
    def create(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        logger.info(f"validated data = {validated_data}")

        requested_workflow = validated_data.get('workflow')

        if requested_workflow is None:
            raise serializers.ValidationError({
                'workflow': [ErrorDetail('Workflow is required', code='missing')]
            })

        ensure_group_access_level(group=requested_workflow.created_by_group,
                min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK,
                run_environment=requested_workflow.run_environment)

        if not requested_workflow.can_start_execution():
            return Response(status=status.HTTP_409_CONFLICT)

        saved = serializer.save()

        if saved.status == WorkflowExecution.Status.MANUALLY_STARTED:
            saved.manually_start()

        requested_workflow.latest_workflow_execution = saved
        requested_workflow.save()

        return self.respond_with_workflow_execution(request, workflow_execution=saved,
            status_code=status.HTTP_201_CREATED)

    def respond_with_workflow_execution(self, request: Request,
            workflow_execution: WorkflowExecution, status_code=status.HTTP_200_OK):
        serializer = WorkflowExecutionSerializer(instance=workflow_execution,
                                                 context={'request': request})
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status_code, headers=headers)
