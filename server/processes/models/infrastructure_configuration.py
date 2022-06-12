from django.db import models

class InfrastructureConfiguration(models.Model):
    class Meta:
        abstract = True

    infrastructure_type = models.CharField(max_length=100, null=False,
        blank=True, default='')
    infrastructure_settings = models.JSONField(null=True, blank=True)
