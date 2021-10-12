from django.db import models

from . import Alert


class InsufficientServiceInstancesAlert(Alert):
    event = models.ForeignKey('InsufficientServiceInstancesEvent',
                              on_delete=models.CASCADE)
