from django.db import models

from .missing_scheduled_execution import MissingScheduledExecution

class MissingScheduledWorkflowExecution(MissingScheduledExecution):
    workflow = models.ForeignKey('Workflow', on_delete=models.CASCADE)

    @property
    def schedulable_instance(self):
        return self.workflow
