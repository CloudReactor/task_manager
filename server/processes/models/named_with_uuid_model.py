from typing import Optional, TYPE_CHECKING

from django.db import models

from django.contrib.auth.models import Group, User

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from processes.exception import UnprocessableEntity

from .uuid_model import UuidModel

if TYPE_CHECKING:
    from .run_environment import RunEnvironment

class NamedWithUuidModel(UuidModel):
    class Meta:
        abstract = True

    name = models.CharField(max_length=200)
    description = models.CharField(max_length=5000, blank=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL,
            null=True, editable=True)
    created_by_group = models.ForeignKey(Group, on_delete=models.CASCADE,
            editable=True)

    @classmethod
    def find_by_uuid_or_name(cls, obj_dict,
            required_group: Optional[Group] = None,
            required_run_environment: 'Optional[RunEnvironment]' = None,
            check_conflict: bool = True,
            allowed_run_environment: 'Optional[RunEnvironment]' = None,
            allow_any_run_environment: Optional[bool] = None):
        uuid = obj_dict.get('uuid')
        name = obj_dict.get('name')

        if uuid is not None:
            entity = cls.objects.get(uuid=uuid)

            if check_conflict and (name is not None) and (entity.name != name):
                raise UnprocessableEntity(
                        f"{cls.__name__} {uuid} is named '{entity.name}', not '{name}'")
        else:
            if name is None:
                raise serializers.ValidationError('Neither uuid or name found in request')

            entity = cls.objects.get(name=name, created_by_group=required_group)

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

    def __str__(self) -> str:
        return (self.name or 'Unnamed') + ' / ' + str(self.uuid)
