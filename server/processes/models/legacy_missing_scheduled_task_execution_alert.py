from django.db import models

from .alert import Alert


class LegacyMissingScheduledTaskExecutionAlert(Alert):
    missing_scheduled_task_execution = models.ForeignKey('LegacyMissingScheduledTaskExecution',
            on_delete=models.CASCADE,
            db_column='missing_scheduled_process_execution_id')

    class Meta:
        db_table = 'processes_missingscheduledprocessexecutionalert'
