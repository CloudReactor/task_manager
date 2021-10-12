from django.db import models

from .alert import Alert

class TaskExecutionAlert(Alert):
    task_execution = models.ForeignKey('TaskExecution',
            on_delete=models.CASCADE,
            db_column='process_execution_id')

    class Meta:
        db_table = 'processes_processexecutionalert'
