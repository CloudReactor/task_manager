from django.db import models

from .event import Event
from .workflow_execution import WorkflowExecution

class WorkflowExecutionEvent(Event):
    workflow_execution = models.ForeignKey(WorkflowExecution, null=True, on_delete=models.CASCADE)

    def __str__(self):
        we_id = str(self.workflow_execution.uuid) if self.workflow_execution else '[REMOVED]'
        return 'Workflow Execution ' + we_id + ' / ' + str(self.uuid)
