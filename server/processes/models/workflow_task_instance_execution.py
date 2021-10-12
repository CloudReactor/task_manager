from typing import cast
import logging
import uuid

from django.db import models

logger = logging.getLogger(__name__)


class WorkflowTaskInstanceExecution(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_latest = models.BooleanField(default=True)

    workflow_execution = models.ForeignKey('WorkflowExecution',
            on_delete=models.CASCADE)

    workflow_task_instance = models.ForeignKey(
            'WorkflowTaskInstance', on_delete=models.CASCADE,
            db_column='workflow_process_type_instance_id')

    task_execution = models.OneToOneField('TaskExecution',
            on_delete=models.CASCADE,
            db_column='process_execution_id')

    class Meta:
        db_table = 'processes_workflowprocesstypeinstanceexecution'
        ordering = ['created_at']

    def __str__(self) -> str:
        return str(self.uuid)

    def handle_task_execution_finished(self) -> None:
        from .workflow_execution import WorkflowExecution
        we = cast(WorkflowExecution, self.workflow_execution)
        we.handle_workflow_task_instance_execution_finished(self,
                skipped=False)
