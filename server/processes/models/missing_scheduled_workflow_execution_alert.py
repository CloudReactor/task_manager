from django.db import models

from . import Alert


class MissingScheduledWorkflowExecutionAlert(Alert):
    missing_scheduled_workflow_execution = models.ForeignKey('MissingScheduledWorkflowExecution', on_delete=models.CASCADE)
