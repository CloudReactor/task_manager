from django.db import models

from django.core.validators import MaxValueValidator, MinValueValidator

class ExecutionProbabilities(models.Model):
    class Meta:
        abstract = True

    managed_probability = models.FloatField(null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    failure_report_probability =  models.FloatField(null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    timeout_report_probability =  models.FloatField(null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
