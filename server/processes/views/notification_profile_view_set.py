import logging
from typing import Any

from django_filters import CharFilter
from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter

from drf_spectacular.utils import extend_schema

from rest_framework.request import Request

from ..models import NotificationProfile
from ..serializers import NotificationProfileSerializer

from .base_view_set import BaseViewSet
from .atomic_viewsets import AtomicModelViewSet
from .cloning_mixin import CloningMixin

logger = logging.getLogger(__name__)


class NotificationProfileFilter(filters.FilterSet):
    name = CharFilter()
    created_by_group__id = NumberFilter()
    run_environment__uuid = CharFilter()

    class Meta:
        model = NotificationProfile
        fields = ['name', 'created_by_group__id', 'run_environment__uuid']

    @property
    def qs(self):
        parent = super().qs

        optional_run_environment_uuid = self.request.query_params.get(
            'optional_run_environment__uuid')

        if optional_run_environment_uuid is None:
            return parent
        else:
            return parent.filter(
              run_environment__uuid=optional_run_environment_uuid) | \
              parent.filter(run_environment__uuid__isnull=True)

@extend_schema(responses=NotificationProfileSerializer)
class NotificationProfileViewSet(AtomicModelViewSet, CloningMixin, BaseViewSet):
    model_class = NotificationProfile
    serializer_class = NotificationProfileSerializer
    filterset_class = NotificationProfileFilter
    search_fields = ('uuid', 'name', 'description',)
    ordering_fields = ('uuid', 'name', 'run_environment__name',)

    def make_clone(self, request: Request, entity: Any) -> Any:
        # Save the ManyToMany relationships before cloning
        notification_delivery_methods = list(entity.notification_delivery_methods.all())
        
        # Clone the entity using the parent implementation
        cloned_entity = super().make_clone(request=request, entity=entity)
        
        # Restore the ManyToMany relationships
        cloned_entity.notification_delivery_methods.set(notification_delivery_methods)
        
        return cloned_entity
