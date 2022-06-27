import uuid

from django.db import models


class MissingScheduledExecution(models.Model):
    class Meta:
        abstract = True

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    expected_execution_at = models.DateTimeField()
    schedule = models.CharField(max_length=1000)
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True)

    @property
    def schedulable_instance(self):
        pass
