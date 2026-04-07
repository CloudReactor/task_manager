# From https://gist.github.com/prudnikov/3a968a1ee1cf9b02730cc40bc1d3d9f2
from __future__ import annotations

import logging

from typing import Any
from django.db import transaction

from rest_framework import mixins
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..exception import CommittableException

__all__ = ['AtomicCreateModelMixin', 'AtomicUpdateModelMixin', 'AtomicDestroyModelMixin',
           'AtomicModelViewSetMixin', 'AtomicModelViewSet']

logger = logging.getLogger(__name__)


class AtomicContextManager:
    def __init__(self) -> None:
        self.saved_rv: Any | None = None
        self.saved_ex: Exception | None = None
        self.atomic: Any | None = None

    def __enter__(self) -> AtomicContextManager:
        self.atomic = transaction.atomic()

        if self.atomic is None:
            raise APIException("Can't start transaction")

        self.atomic.__enter__()

        return self


    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None,
            traceback: Any) -> None:
        if self.atomic is None:
            raise exc_value or APIException("Can't commit transaction")

        try:
            if isinstance(exc_value, CommittableException):
                logger.info(f"Committing after exception: {exc_value}")
                self.atomic.__exit__(exc_type=None, exc_value=None, traceback=None)
                raise exc_value.cause or APIException("Partial failure")

            self.atomic.__exit__(exc_type=exc_type, exc_value=exc_value, traceback=traceback)
        finally:
            self.atomic = None

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
