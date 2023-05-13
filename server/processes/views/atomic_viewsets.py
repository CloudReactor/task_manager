# From https://gist.github.com/prudnikov/3a968a1ee1cf9b02730cc40bc1d3d9f2

from typing import Any, Optional
from django.db import transaction

from rest_framework import mixins
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from processes.exception import CommittableException

__all__ = ['AtomicCreateModelMixin', 'AtomicUpdateModelMixin', 'AtomicDestroyModelMixin',
           'AtomicModelViewSetMixin', 'AtomicModelViewSet']


class AtomicContextManager:
    def __init__(self):
        self.sid = None

    def __enter__(self):
        self.sid = transaction.savepoint()


    def __exit__(self, exc_type: Optional[Any], exc_value: Optional[Exception], exc_tb: Optional[Any]):
        if isinstance(exc_value, CommittableException):
            transaction.savepoint_commit(self.sid)
            raise exc_value.cause
        elif exc_value:
            transaction.savepoint_rollback(self.sid)
            raise exc_value
        else:
            transaction.savepoint_commit(self.sid)


class AtomicCreateModelMixin(mixins.CreateModelMixin):
    def create(self, request: Request, *args, **kwargs) -> Response:
        with AtomicContextManager():
            return super().create(request, *args, **kwargs)


class AtomicUpdateModelMixin(mixins.UpdateModelMixin):
    def update(self, request: Request, *args, **kwargs) -> Response:
        with AtomicContextManager():
            return super().update(request, *args, **kwargs)


class AtomicDestroyModelMixin(mixins.DestroyModelMixin):
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        with AtomicContextManager():
            return super().destroy(request, *args, **kwargs)


class AtomicModelViewSetMixin(AtomicUpdateModelMixin, AtomicCreateModelMixin,
        AtomicDestroyModelMixin):
    pass


class AtomicModelViewSet(AtomicCreateModelMixin, mixins.RetrieveModelMixin,
      AtomicUpdateModelMixin, AtomicDestroyModelMixin, mixins.ListModelMixin,
      GenericViewSet):
    pass
