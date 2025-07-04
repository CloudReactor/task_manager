from django.db import models

from .legacy_missing_scheduled_execution import LegacyMissingScheduledExecution

class LegacyMissingScheduledTaskExecution(LegacyMissingScheduledExecution):
    task = models.ForeignKey('Task', on_delete=models.CASCADE,
            db_column='process_type_id')

    class Meta:
        db_table = 'processes_missingscheduledprocessexecution'

    @property
    def schedulable_instance(self):
        return self.task
