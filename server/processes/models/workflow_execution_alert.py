from django.db import models

from .alert import Alert

class WorkflowExecutionAlert(Alert):
    workflow_execution = models.ForeignKey('WorkflowExecution', on_delete=models.CASCADE)
    for_latest_execution = models.BooleanField(default=True)
