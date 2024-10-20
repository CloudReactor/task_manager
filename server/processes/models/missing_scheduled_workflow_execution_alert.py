from django.db import models

from .alert import Alert


class MissingScheduledWorkflowExecutionAlert(Alert):
    missing_scheduled_workflow_execution = models.ForeignKey('MissingScheduledWorkflowExecution', on_delete=models.CASCADE)
