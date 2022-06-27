import logging
import uuid

from django.db import models

logger = logging.getLogger(__name__)


class WorkflowTransitionEvaluation(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    result = models.BooleanField()

    # Can be gotten from from_workflow_task_instance_execution, but leave for now
    workflow_execution = models.ForeignKey(
        'WorkflowExecution', on_delete=models.CASCADE)

    # TODO: don't allow null
    from_workflow_task_instance_execution = models.ForeignKey(
        'WorkflowTaskInstanceExecution', null=True,
        on_delete=models.CASCADE,
        db_column='from_workflow_process_type_instance_execution_id')

    workflow_transition = models.ForeignKey(
        'WorkflowTransition', on_delete=models.CASCADE)

    class Meta:
        ordering = ['evaluated_at']
