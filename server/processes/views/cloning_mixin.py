from typing import Any

import logging
import uuid as python_uuid

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ..common.request_helpers import (
    ensure_group_access_level
)
from ..common.utils import generate_clone_name
from ..models import UserGroupAccessLevel

from .base_view_set import BaseViewSet

logger = logging.getLogger(__name__)


class CloningMixin(BaseViewSet):
    @transaction.atomic
    @action(methods=['post'], detail=True,
            url_path='clone', url_name='clone')
    def clone(self, request: Request, uuid: str):
        entity = self.model_class.objects.get(uuid=uuid)

        ensure_group_access_level(group=entity.created_by_group,
            min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            run_environment=None, allow_api_key=True, request=request)

        cloned_entity = self.make_clone(request=request, entity=entity)

        serializer = self.get_serializer(cloned_entity, context={'request': request})
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def make_clone(self, request: Request, entity: Any) -> Any:
        data = request.data
        entity.pk = None
        entity.uuid = python_uuid.uuid4()
        entity.name = data.get('name', generate_clone_name(getattr(entity, 'name')))
        entity.created_at = timezone.now()
        entity.updated_at = timezone.now()
        entity.save()
        return entity
