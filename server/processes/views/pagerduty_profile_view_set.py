from django_filters import CharFilter
from django_filters import rest_framework as filters
from django_filters.filters import NumberFilter

from ..models import PagerDutyProfile
from ..serializers import PagerDutyProfileSerializer

from .base_view_set import BaseViewSet
from .atomic_viewsets import AtomicModelViewSet
from .cloning_mixin import CloningMixin


class PagerDutyProfileFilter(filters.FilterSet):
    name = CharFilter()
    created_by_group__id = NumberFilter()
    run_environment__uuid = CharFilter()

    class Meta:
        model = PagerDutyProfile
        fields = ['name', 'created_by_group__id', 'run_environment__uuid']


class PagerDutyProfileViewSet(CloningMixin, AtomicModelViewSet, BaseViewSet):
    model_class = PagerDutyProfile
    serializer_class = PagerDutyProfileSerializer
    filterset_class = PagerDutyProfileFilter
    search_fields = ('uuid', 'name', 'description',)
    ordering_fields = ('uuid', 'name', 'run_environment__name',)
