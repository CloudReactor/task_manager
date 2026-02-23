from typing import override

from django.db import models

from .workflow_event import WorkflowEvent
from .workflow_execution import WorkflowExecution

class WorkflowExecutionEvent(WorkflowEvent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.workflow_execution:
            self.workflow = self.workflow or self.workflow_execution.workflow

            if not self.run_environment:
                self.run_environment = self.workflow_execution.run_environment

            if not self.created_by_group:
                self.created_by_group = self.workflow_execution.created_by_group

        if self.workflow:
            if not self.created_by_group:
                self.created_by_group = self.workflow.created_by_group

            if not self.run_environment:
                self.run_environment = self.workflow.run_environment

            if not self.created_by_group:
                self.created_by_group = self.workflow.created_by_group

        if self.run_environment:
            if not self.created_by_group:
                self.created_by_group = self.run_environment.created_by_group

    @override
    def __str__(self) -> str:
        we_id = str(self.workflow_execution.uuid) if self.workflow_execution else '[REMOVED]'
        return 'Workflow Execution ' + we_id + ' / ' + str(self.uuid)
