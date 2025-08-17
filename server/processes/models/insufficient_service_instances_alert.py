from django.db import models

from .alert import Alert


class InsufficientServiceInstancesAlert(Alert):
    event = models.ForeignKey('LegacyInsufficientServiceInstancesEvent',
                              on_delete=models.CASCADE)
