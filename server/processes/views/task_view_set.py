import logging

from django.db.models import Prefetch

from django.contrib.auth.models import User

from django_filters import CharFilter
from django_filters import rest_framework as filters

from processes.models import Task, RunEnvironment, AlertMethod
from processes.serializers import TaskSerializer

from .base_view_set import BaseViewSet
from .atomic_viewsets import (
    AtomicCreateModelMixin, AtomicUpdateModelMixin, AtomicDestroyModelMixin
)


logger = logging.getLogger(__name__)


class TaskFilter(filters.FilterSet):
    name = CharFilter()
    description = CharFilter()

    class Meta:
        model = Task
        fields = ['name', 'description', 'passive', 'run_environment__uuid']

    @property
    def qs(self):
        parent = super().qs
        is_service = self.request.query_params.get('is_service', None)

        if is_service:
            is_service = (str(is_service).lower() == 'true')

        if is_service is None:
            return parent
        else:
            return parent.filter(service_instance_count__isnull=not is_service)


class TaskViewSet(AtomicCreateModelMixin, AtomicUpdateModelMixin,
        AtomicDestroyModelMixin, BaseViewSet):
    model_class = Task
    filterset_class = TaskFilter
    serializer_class = TaskSerializer
    search_fields = ('name', 'description')
    ordering_fields = (
        'uuid', 'name', 'enabled', 'is_service', 'schedule',
        'heartbeat_interval_seconds', 'max_concurrency', 'max_age_seconds',
        'default_max_retries', 'passive',
        'run_environment__name',
        'latest_task_execution__started_at',
        'latest_task_execution__finished_at',
        'latest_task_execution__last_heartbeat_at',
        'latest_task_execution__status',
        'latest_task_execution__success_count',
        'latest_task_execution__error_count',
        'latest_task_execution__skipped_count',)

    def get_queryset(self):
        omitted = (self.request.query_params.get('omit') or '').split(',')
        run_environment_qs = RunEnvironment.objects.only('uuid', 'name', 'aws_default_region')
        user_qs = User.objects.only('username')

        qs = super().get_queryset().select_related('latest_task_execution__started_by',
            #'latest_task_execution__marked_done_by', 'latest_task_execution__killed_by',
            #'latest_task_execution__task', # HACK, not sure why this is needed to prevent N+1
            'created_by_group').\
            prefetch_related(
                Prefetch('created_by_user', queryset=user_qs),
                Prefetch('run_environment', queryset=run_environment_qs))

        if 'links' not in omitted:
            qs = qs.prefetch_related('tasklink_set')

        if 'alert_methods' not in omitted:
            alert_methods_qs = AlertMethod.objects.only('uuid', 'name')
            qs = qs.prefetch_related(Prefetch('alert_methods', queryset=alert_methods_qs))

        return qs
