# From https://gist.github.com/prudnikov/3a968a1ee1cf9b02730cc40bc1d3d9f2

from django.db import transaction

from rest_framework import mixins
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

__all__ = ['AtomicCreateModelMixin', 'AtomicUpdateModelMixin', 'AtomicDestroyModelMixin',
           'AtomicModelViewSetMixin', 'AtomicModelViewSet']


class AtomicCreateModelMixin(mixins.CreateModelMixin):
    @transaction.atomic
    def create(self, request: Request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class AtomicUpdateModelMixin(mixins.UpdateModelMixin):
    @transaction.atomic
    def update(self, request: Request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class AtomicDestroyModelMixin(mixins.DestroyModelMixin):
    @transaction.atomic
    def destroy(self, request: Request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class AtomicModelViewSetMixin(AtomicUpdateModelMixin, AtomicCreateModelMixin,
        AtomicDestroyModelMixin):
    pass


class AtomicModelViewSet(AtomicCreateModelMixin, mixins.RetrieveModelMixin,
      AtomicUpdateModelMixin, AtomicDestroyModelMixin, mixins.ListModelMixin,
      GenericViewSet):
    pass
