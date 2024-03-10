import logging

from django.db import transaction

from django_filters import CharFilter
from django_filters import rest_framework as filters

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from processes.models import Workflow, WorkflowExecution
from processes.serializers import WorkflowSerializer, WorkflowSummarySerializer

from .base_view_set import BaseViewSet
from .atomic_viewsets import AtomicCreateModelMixin, AtomicUpdateModelMixin, AtomicDestroyModelMixin

logger = logging.getLogger(__name__)


class WorkflowFilter(filters.FilterSet):
    class Meta:
        model = Workflow
        fields = {
            'name': ['exact'],
            'description': ['exact'],
            'run_environment__uuid': ['exact', 'in'],
        }

    @property
    def qs(self):
        rv = super().qs

        status_list_str = self.request.query_params.get('latest_workflow_execution__status')

        if status_list_str:
            status_strings = status_list_str.split(',')
            statuses = [WorkflowExecution.Status[s.upper()].value for s in status_strings]
            rv = rv.filter(latest_workflow_execution__status__in=statuses)

        return rv

class WorkflowViewSet(AtomicCreateModelMixin, AtomicUpdateModelMixin,
        AtomicDestroyModelMixin, BaseViewSet):
    model_class = Workflow
    filterset_class = WorkflowFilter
    search_fields = ('name', 'description',)
    ordering_fields = (
        'uuid', 'name', 'enabled', 'run_environment__name',
        'latest_workflow__started_at',
        'latest_workflow_execution__finished_at',
        'latest_workflow_execution__started_at',
        'latest_workflow_execution__status',
    )

    def get_queryset(self):
        qs = super().get_queryset().select_related('latest_workflow_execution',
                'created_by_user', 'created_by_group')

        if self.action != 'list':
            qs = qs.prefetch_related('workflow_task_instances__task')

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowSummarySerializer
        else:
            return WorkflowSerializer

    @transaction.atomic
    @action(methods=['post'], detail=True,
            url_path='clone', url_name='clone')
    def clone(self, request: Request, uuid=None):
        workflow = Workflow.objects.get(uuid=uuid)
        self.check_object_permissions(request, workflow)
        cloned = workflow.clone(request.data)
        serializer = WorkflowSerializer(instance=cloned,
                                        context={'request': request})
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
