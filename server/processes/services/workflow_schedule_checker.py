import logging

from processes.models import *
from processes.serializers.missing_scheduled_workflow_execution_serializer import \
    MissingScheduledWorkflowExecutionSerializer
from .schedule_checker import ScheduleChecker

SUMMARY_TEMPLATE = \
    """Workflow '{{workflow.name}}' did not execute as scheduled at {{expected_execution_at}}"""

logger = logging.getLogger(__name__)


class WorkflowScheduleChecker(ScheduleChecker):
    def model_name(self):
        return 'workflow'

    def manager(self):
        return Workflow.objects

    def missing_scheduled_executions_of(self, schedulable):
        return MissingScheduledWorkflowExecution.objects.filter(workflow=schedulable)

    def executions_of(self, schedulable):
        return WorkflowExecution.objects.filter(workflow=schedulable)

    def make_missing_scheduled_execution(self, schedulable, expected_execution_at):
        return MissingScheduledWorkflowExecution(workflow=schedulable,
                                                 schedule=schedulable.schedule,
                                                 expected_execution_at=expected_execution_at)

    def missing_scheduled_execution_to_details(self, mse, context):
        return MissingScheduledWorkflowExecutionSerializer(mse, context=context).data

    def make_missing_execution_alert(self, mse, alert_method):
        return MissingScheduledWorkflowExecutionAlert(missing_scheduled_workflow_execution=mse,
                                                      alert_method=alert_method)

    def alert_summary_template(self):
        return SUMMARY_TEMPLATE
