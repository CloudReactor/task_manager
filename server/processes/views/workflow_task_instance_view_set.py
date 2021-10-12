from typing import cast, Any, Optional

import logging

from django.db.models.query import QuerySet
from django.contrib.auth.models import Group

from django_filters import CharFilter
from django_filters import rest_framework as filters

from rest_framework import permissions

from ..models import (
    RunEnvironment,
    Workflow,
    WorkflowTaskInstance
)
from ..permissions import IsCreatedByGroup
from ..serializers import WorkflowTaskInstanceSerializer
from ..common.request_helpers import (
    extract_filtered_group
)

from .atomic_viewsets import (
    AtomicCreateModelMixin,
    AtomicUpdateModelMixin,
    AtomicDestroyModelMixin
)
from .base_view_set import BaseViewSet


logger = logging.getLogger(__name__)


class WorkflowTaskInstancePermission(IsCreatedByGroup):
    def group_for_object(self, obj: Any) -> Optional[Group]:
        wti = cast(WorkflowTaskInstance, obj)
        return wti.workflow.created_by_group

    def run_environment_for_object(self, obj: Any) -> Optional[RunEnvironment]:
        wti = cast(WorkflowTaskInstance, obj)
        return wti.workflow.run_environment


class WorkflowTaskInstanceFilter(filters.FilterSet):
    name = CharFilter()
    description = CharFilter()

    class Meta:
        model = WorkflowTaskInstance
        fields = ['name', 'description', 'workflow__uuid',
            'workflow__created_by_group__id',
            'workflow__run_environment__uuid', 'task__uuid',
            'task__name']


class WorkflowTaskInstanceViewSet(AtomicCreateModelMixin,
        AtomicUpdateModelMixin, AtomicDestroyModelMixin, BaseViewSet):
    model_class = WorkflowTaskInstance
    serializer_class = WorkflowTaskInstanceSerializer
    lookup_field = 'uuid'
    permission_classes = (permissions.IsAuthenticated, WorkflowTaskInstancePermission,)
    filterset_class = WorkflowTaskInstanceFilter
    search_fields = ('uuid', 'name', 'description', 'workflow__name',
            'task__name',)
    ordering_fields = ('name', 'workflow__name', 'uuid')
    ordering = 'name'
    def get_queryset(self):
        return super().get_queryset().select_related(
            'workflow__created_by_group',
            'workflow__run_environment',
            'task__created_by_group')

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
