from datetime import datetime
import logging

from typing import cast

from processes.models import *
from processes.serializers.missing_scheduled_workflow_execution_serializer import \
    LegacyMissingScheduledWorkflowExecutionSerializer
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
        return LegacyMissingScheduledWorkflowExecution.objects.filter(
                workflow=schedulable)

    def executions_of(self, schedulable: Workflow):
        return WorkflowExecution.objects.filter(workflow=schedulable)

    def make_missing_scheduled_execution(self, schedulable: Workflow,
            expected_execution_at: datetime) -> LegacyMissingScheduledWorkflowExecution:
        return LegacyMissingScheduledWorkflowExecution(workflow=schedulable,
                schedule=schedulable.schedule,
                expected_execution_at=expected_execution_at)

    def missing_scheduled_execution_to_details(self,
            mse: LegacyMissingScheduledExecution, context) -> dict:
        return LegacyMissingScheduledWorkflowExecutionSerializer(mse,
                context=context).data

    def make_missing_execution_alert(self, mse: LegacyMissingScheduledExecution,
            alert_method: AlertMethod) -> LegacyMissingScheduledWorkflowExecutionAlert:
        return LegacyMissingScheduledWorkflowExecutionAlert(
                missing_scheduled_workflow_execution=cast(
                        LegacyMissingScheduledWorkflowExecution, mse),
                alert_method=alert_method)

    def alert_summary_template(self) -> str:
        return SUMMARY_TEMPLATE
