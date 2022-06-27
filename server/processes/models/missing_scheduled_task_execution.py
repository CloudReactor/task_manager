from django.db import models

from . import MissingScheduledExecution

class MissingScheduledTaskExecution(MissingScheduledExecution):
    task = models.ForeignKey('Task', on_delete=models.CASCADE,
            db_column='process_type_id')

    class Meta:
        db_table = 'processes_missingscheduledprocessexecution'

    @property
    def schedulable_instance(self):
        return self.task
