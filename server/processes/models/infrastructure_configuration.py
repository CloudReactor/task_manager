from typing import TYPE_CHECKING

from django.db import models

from ..execution_methods.aws_settings import AwsSettings, INFRASTRUCTURE_TYPE_AWS
from ..execution_methods.infrastructure_settings import InfrastructureSettings

class InfrastructureConfiguration(models.Model):
    class Meta:
        abstract = True

    infrastructure_type = models.CharField(max_length=100, null=False,
        blank=True, default='')
    infrastructure_settings = models.JSONField(null=True, blank=True)

    def parsed_infrastructure_settings(self) -> InfrastructureSettings | None:
        if not self.infrastructure_settings:
            return None

        if self.infrastructure_type == INFRASTRUCTURE_TYPE_AWS:
            return AwsSettings.parse_obj(self.infrastructure_settings)

        return None
