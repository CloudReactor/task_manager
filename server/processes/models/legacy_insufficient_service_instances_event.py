import uuid

from django.db import models


class LegacyInsufficientServiceInstancesEvent(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    task = models.ForeignKey('Task', on_delete=models.CASCADE,
            db_column='process_type_id')
    interval_start_at = models.DateTimeField()
    interval_end_at = models.DateTimeField()
    detected_concurrency = models.IntegerField()
    required_concurrency = models.IntegerField()
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['detected_at']
        db_table = 'processes_insufficientserviceinstancesevent'

    def __str__(self):
        return self.task.name + ' / ' + str(self.uuid)
