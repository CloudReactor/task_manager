from datetime import datetime
import logging

from typing import cast

from processes.models import *
from processes.serializers.missing_scheduled_workflow_execution_serializer import \
    MissingScheduledWorkflowExecutionSerializer
from .schedule_checker import ScheduleChecker

SUMMARY_TEMPLATE = \
    """Workflow '{{workflow.name}}' did not execute as scheduled at {{expected_execution_at}}"""

logger = logging.getLogger(__name__)


class WorkflowScheduleChecker(ScheduleChecker[Workflow]):
    def model_name(self) -> str:
        return 'Workflow'

    def manager(self):
        return Workflow.objects

    def missing_scheduled_executions_of(self, schedulable: Workflow):
        return MissingScheduledWorkflowExecution.objects.filter(
                workflow=schedulable)

    def executions_of(self, schedulable: Workflow):
        return WorkflowExecution.objects.filter(workflow=schedulable)

    def make_missing_scheduled_execution(self, schedulable: Workflow,
            expected_execution_at: datetime) -> MissingScheduledWorkflowExecution:
        return MissingScheduledWorkflowExecution(workflow=schedulable,
                schedule=schedulable.schedule,
                expected_execution_at=expected_execution_at)

    def missing_scheduled_execution_to_details(self,
            mse: MissingScheduledExecution, context) -> dict:
        return MissingScheduledWorkflowExecutionSerializer(mse,
                context=context).data

    def make_missing_execution_alert(self, mse: MissingScheduledExecution,
            alert_method: AlertMethod) -> MissingScheduledWorkflowExecutionAlert:
        return MissingScheduledWorkflowExecutionAlert(
                missing_scheduled_workflow_execution=cast(
                        MissingScheduledWorkflowExecution, mse),
                alert_method=alert_method)

    def alert_summary_template(self) -> str:
        return SUMMARY_TEMPLATE
