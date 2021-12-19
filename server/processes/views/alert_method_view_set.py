import logging

from django_filters import CharFilter
from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter

from drf_spectacular.utils import extend_schema

from ..models import AlertMethod
from ..serializers import AlertMethodSerializer

from .base_view_set import BaseViewSet
from .atomic_viewsets import AtomicModelViewSet
from .cloning_mixin import CloningMixin

logger = logging.getLogger(__name__)


class AlertMethodFilter(filters.FilterSet):
    name = CharFilter()
    created_by_group__id = NumberFilter()
    run_environment__uuid = CharFilter()

    class Meta:
        model = AlertMethod
        fields = ['name', 'created_by_group__id', 'run_environment__uuid']

@extend_schema(responses=AlertMethodSerializer)
class AlertMethodViewSet(AtomicModelViewSet, CloningMixin, BaseViewSet):
    model_class = AlertMethod
    serializer_class = AlertMethodSerializer
    filterset_class = AlertMethodFilter
    search_fields = ('uuid', 'name', 'description',)
    ordering_fields = ('uuid', 'name', 'run_environment__name',)
