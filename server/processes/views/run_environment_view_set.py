from typing import Optional

import logging
import uuid as python_uuid

from django.db import transaction
from django.db.models.query import QuerySet
from django.utils import timezone

from django_filters import CharFilter
from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import (
    PermissionDenied
)
from rest_framework.request import Request
from rest_framework.response import Response

from ..common.request_helpers import (
    ensure_group_access_level,
    extract_authenticated_run_environment
)
from ..common.utils import generate_clone_name
from ..models import RunEnvironment, UserGroupAccessLevel
from ..permissions import IsCreatedByGroup
from ..serializers import RunEnvironmentSerializer

from .base_view_set import BaseViewSet
from .atomic_viewsets import (
    AtomicModelViewSet
)

logger = logging.getLogger(__name__)

class RunEnvironmentScopePermission(IsCreatedByGroup):
    def run_environment_for_object(self,
            obj: RunEnvironment) -> Optional[RunEnvironment]:
        return obj

class RunEnvironmentFilter(filters.FilterSet):
    name = CharFilter()
    created_by_group__id = NumberFilter()

    class Meta:
        model = RunEnvironment
        fields = ['name', 'created_by_group__id']


class RunEnvironmentViewSet(AtomicModelViewSet, BaseViewSet):
    model_class = RunEnvironment
    permission_classes = (permissions.IsAuthenticated,
            RunEnvironmentScopePermission)
    serializer_class = RunEnvironmentSerializer
    filterset_class = RunEnvironmentFilter
    search_fields = ('uuid', 'name', 'description')
    ordering_fields = ('uuid', 'name',)
    ordering = 'name'

    def filter_queryset_by_run_environment(self, qs: QuerySet,
            run_environment: RunEnvironment) -> QuerySet:
        return qs.filter(pk=run_environment.pk)

    @transaction.atomic
    def create(self, request: Request, *args, **kwargs):
        run_environment = extract_authenticated_run_environment(request)

        if run_environment is not None:
            raise PermissionDenied('An API key scoped to a Run Environment cannot be used to create another Run Envionment')

        return super().create(request, *args, **kwargs)

    @transaction.atomic
    @action(methods=['post'], detail=True,
            url_path='clone', url_name='clone')
    def clone(self, request: Request, uuid=None):
        run_environment = RunEnvironment.objects.get(uuid=uuid)

        ensure_group_access_level(group=run_environment.created_by_group,
            min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            run_environment=None, allow_api_key=True, request=request)

        data = request.data

        run_environment.pk = None
        run_environment.uuid = python_uuid.uuid4()
        run_environment.name = data.get('name', generate_clone_name(run_environment.name))
        run_environment.created_at = timezone.now()
        run_environment.updated_at = timezone.now()

        run_environment.save()

        serializer = RunEnvironmentSerializer(instance=run_environment,
                context={'request': request})
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
