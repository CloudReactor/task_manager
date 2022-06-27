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
    WorkflowTransition
)
from ..permissions import IsCreatedByGroup
from ..serializers import WorkflowTransitionSerializer
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


class WorkflowTransitionPermission(IsCreatedByGroup):
    def group_for_object(self, obj: Any) -> Optional[Group]:
        wt = cast(WorkflowTransition, obj)
        return wt.workflow.created_by_group

    def run_environment_for_object(self, obj: Any) -> Optional[RunEnvironment]:
        wt = cast(WorkflowTransition, obj)
        return wt.workflow.run_environment


class WorkflowTransitionFilter(filters.FilterSet):
    description = CharFilter()

    class Meta:
        model = WorkflowTransition
        fields = ['description']


class WorkflowTransitionViewSet(AtomicCreateModelMixin,
        AtomicUpdateModelMixin, AtomicDestroyModelMixin, BaseViewSet):
    lookup_field = 'uuid'
    permission_classes = (permissions.IsAuthenticated, WorkflowTransitionPermission,)
    serializer_class = WorkflowTransitionSerializer
    model_class = WorkflowTransition
    filterset_class = WorkflowTransitionFilter
    search_fields = ('uuid', 'description',)
    ordering_fields = (
        'uuid',
    )
    ordering = 'uuid'

    def get_queryset(self):
        qs = super().get_queryset().select_related(
                'from_workflow_task_instance__workflow__created_by_group',
                'to_workflow_task_instance__workflow__created_by_group',)

        workflow_uuid = self.request.query_params.get('workflow__uuid')

        if workflow_uuid:
            qs = qs.filter(from_workflow_task_instance__workflow__uuid=workflow_uuid)

        return qs

    def filter_queryset_by_group(self, qs: QuerySet, group: Group) -> QuerySet:
        return qs.filter(from_workflow_task_instance__workflow__created_by_group=group)


    def filter_queryset_by_run_environment(self, qs: QuerySet,
            run_environment: RunEnvironment) -> QuerySet:
        return qs.filter(from_workflow_task_instance__workflow__run_environment=run_environment)

    def get_queryset_for_all_groups(self) -> QuerySet:
        return self.model_class.objects.filter(
            from_workflow_task_instance__workflow__created_by_group__in=self.request.user.groups.all()
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
