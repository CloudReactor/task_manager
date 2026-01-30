from __future__ import annotations

from typing import TYPE_CHECKING, override

import uuid

from django.conf import settings
from django.db import models

from django.contrib.auth.models import Group

import stringcase


from rest_framework import serializers
from rest_framework.exceptions import NotFound

from ..exception.unprocessable_entity import UnprocessableEntity

if TYPE_CHECKING:
    from .run_environment import RunEnvironment

class UuidModel(models.Model):
    class Meta:
        abstract = True

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    @override
    def __str__(self) -> str:
        return str(self.uuid)

    @classmethod
    def find_by_uuid(cls, obj_dict,
            required_group: Group | None = None,
            required_run_environment: RunEnvironment | None = None,
            check_conflict: bool = False,
            allowed_run_environment: RunEnvironment | None = None,
            allow_any_run_environment: bool | None = None):        
        return cls.find_by_uuid_or_name_core(
            obj_dict,
            required_group=required_group,
            required_run_environment=required_run_environment,
            check_conflict=check_conflict,
            allowed_run_environment=allowed_run_environment,
            allow_any_run_environment=allow_any_run_environment,
            use_name=False)


    @classmethod
    def find_by_uuid_or_name_core(cls, obj_dict,
            required_group: Group | None,
            required_run_environment: RunEnvironment | None,
            check_conflict: bool,
            allowed_run_environment: RunEnvironment | None,
            allow_any_run_environment: bool | None,
            use_name: bool):       
        uuid = obj_dict.get('uuid')
        name = obj_dict.get('name') if use_name else None

        if uuid is not None:
            entity = cls.objects.get(uuid=uuid)

            if check_conflict and (name is not None) and (entity.name != name):
                raise UnprocessableEntity(
                        f"{cls.__name__} {uuid} is named '{entity.name}', not '{name}'")
        elif use_name:
            if name is None:
                raise serializers.ValidationError('Neither uuid or name found in request')
            
            entity = cls.objects.get(name=name, created_by_group=required_group)
        else:
            raise serializers.ValidationError('uuid not found in request')
        
        if required_group and (entity.created_by_group != required_group):
            raise NotFound()

        if required_run_environment and (
                entity.run_environment != required_run_environment):
            raise NotFound()

        # So that allowed_run_environment can be omitted if
        # required_run_environment is set
        allowed_run_environment = allowed_run_environment or \
                required_run_environment

        if allow_any_run_environment is None:
            allow_any_run_environment = (allowed_run_environment is None)

        if (not allow_any_run_environment) and \
                hasattr(entity, 'run_environment') and \
                entity.run_environment:

            if allowed_run_environment:
                if entity.run_environment != allowed_run_environment:
                    raise NotFound()
            else:
                raise NotFound()

        return entity
    
    @property
    def dashboard_url(self) -> str:
        return settings.EXTERNAL_BASE_URL + self.dashboard_path \
                + '/' + str(self.uuid)

    @property
    def dashboard_path(self) -> str:
        return stringcase.snakecase(type(self).__name__) + 's'
