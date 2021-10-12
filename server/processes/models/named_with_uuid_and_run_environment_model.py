from django.db import models

from .named_with_uuid_model import NamedWithUuidModel
from .run_environment import RunEnvironment

class NamedWithUuidAndRunEnvironmentModel(NamedWithUuidModel):
    class Meta:
        abstract = True

    run_environment = models.ForeignKey(RunEnvironment,
            on_delete=models.CASCADE, null=True, blank=True)
