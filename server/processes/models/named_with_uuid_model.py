from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from django.contrib.auth.models import Group, User

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
            required_group: Group | None = None,
            required_run_environment: RunEnvironment | None = None,
            check_conflict: bool = True,
            allowed_run_environment: RunEnvironment | None = None,
            allow_any_run_environment: bool | None = None):
        
        return cls.find_by_uuid_or_name_core(
            obj_dict,
            required_group=required_group,
            required_run_environment=required_run_environment,
            check_conflict=check_conflict,
            allowed_run_environment=allowed_run_environment,
            allow_any_run_environment=allow_any_run_environment,
            use_name=True)

    def __str__(self) -> str:
        return (self.name or 'Unnamed') + ' / ' + str(self.uuid)
