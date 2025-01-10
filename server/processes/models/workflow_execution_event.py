from django.db import models

from .event import Event
from .workflow import Workflow
from .workflow_execution import WorkflowExecution

class WorkflowExecutionEvent(Event):
    workflow = models.ForeignKey(Workflow, null=True, on_delete=models.CASCADE)
    workflow_execution = models.ForeignKey(WorkflowExecution, null=True, on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.workflow_execution:
            self.workflow = self.workflow or self.workflow_execution.workflow

        if self.workflow and not self.created_by_group:
            self.created_by_group = self.workflow.created_by_group


    def __str__(self):
        we_id = str(self.workflow_execution.uuid) if self.workflow_execution else '[REMOVED]'
        return 'Workflow Execution ' + we_id + ' / ' + str(self.uuid)
