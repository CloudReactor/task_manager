from typing import Any, Optional, Type

import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.db.models.query import QuerySet

from rest_framework import viewsets
from rest_framework.exceptions import (
    APIException
)

from ..common.request_helpers import (
    extract_filtered_group, extract_authenticated_run_environment,
    required_user_and_group_from_request,
)
from ..models import RunEnvironment

logger = logging.getLogger(__name__)


class BaseReadOnlyViewSetMixin(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'uuid'
    model_class: Type[models.Model]
    ordering_fields: Any = ('name',)
    ordering = 'name'

    def get_queryset(self) -> QuerySet:
        # Prevents this problem in drf-spectacular:
        # failed to obtain model through view's queryset due to raised exception. Prevent this either by setting "queryset = Model.objects.none()" on the view, having an empty fallback in get_queryset() or by using @extend_schema. (Exception: No User found)
        if settings.IN_SCHEMA_GENERATION:
            return self.model_class.objects.none()

        if self.action != 'list':
            return self.get_queryset_for_all_groups()

        _user, request_group = required_user_and_group_from_request(
              request=self.request)

        authenticated_run_environment = extract_authenticated_run_environment(
              request=self.request)

        explicit_group = self.extract_group(request_group=request_group)

        scoped_group = explicit_group or request_group

        if scoped_group is None:
            raise APIException('Missing scoped group')

        return self.get_scoped_queryset(
                group=scoped_group,
                run_environment=authenticated_run_environment)

    def get_scoped_queryset(self, group: Group,
            run_environment: Optional[RunEnvironment]) -> QuerySet:
        qs = self.model_class.objects.all()

        if run_environment:
            if run_environment.created_by_group != group:
                raise APIException('Run Environment Group does not match the authenticated Group')

            return self.filter_queryset_by_run_environment(qs, run_environment)

        return self.filter_queryset_by_group(self.model_class.objects.all(),
                group=group)

    def filter_queryset_by_group(self, qs: QuerySet, group: Group) -> QuerySet:
        return qs.filter(created_by_group=group)

    def filter_queryset_by_run_environment(self, qs: QuerySet,
            run_environment: RunEnvironment) -> QuerySet:
        return qs.filter(run_environment=run_environment)

    def get_queryset_for_all_groups(self) -> QuerySet:
        return self.model_class.objects.filter(
            created_by_group__in=self.request.user.groups.order_by(self.ordering))

    def extract_group(self, request_group: Optional[Group]) -> Optional[Group]:
        return extract_filtered_group(request=self.request,
            request_group=request_group,
            required=(request_group is None),
            parameter_name='created_by_group__id')


class BaseViewSet(BaseReadOnlyViewSetMixin, viewsets.ModelViewSet):
    pass
