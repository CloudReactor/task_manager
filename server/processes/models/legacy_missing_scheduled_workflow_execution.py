from django.db import models

from .legacy_missing_scheduled_execution import LegacyMissingScheduledExecution

class LegacyMissingScheduledWorkflowExecution(LegacyMissingScheduledExecution):
    workflow = models.ForeignKey('Workflow', on_delete=models.CASCADE)

    @property
    def schedulable_instance(self):
        return self.workflow
