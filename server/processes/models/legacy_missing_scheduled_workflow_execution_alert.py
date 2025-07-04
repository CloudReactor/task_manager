from django.db import models

from .alert import Alert


class LegacyMissingScheduledWorkflowExecutionAlert(Alert):
    missing_scheduled_workflow_execution = models.ForeignKey('LegacyMissingScheduledWorkflowExecution', on_delete=models.CASCADE)
