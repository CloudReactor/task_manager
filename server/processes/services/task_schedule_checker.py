import logging

from processes.models import *
from .schedule_checker import ScheduleChecker

SUMMARY_TEMPLATE = \
    """Process '{{task.name}}' did not execute as scheduled at {{expected_execution_at}}"""

logger = logging.getLogger(__name__)


class TaskScheduleChecker(ScheduleChecker):
    def model_name(self):
        return 'process type'

    def manager(self):
        return Task.objects

    def missing_scheduled_executions_of(self, schedulable):
        return MissingScheduledTaskExecution.objects.filter(task=schedulable)

    def executions_of(self, schedulable):
        return TaskExecution.objects.filter(task=schedulable)

    def make_missing_scheduled_execution(self, schedulable, expected_execution_at):
        return MissingScheduledTaskExecution(task=schedulable,
            schedule=schedulable.schedule, expected_execution_at=expected_execution_at)

    def missing_scheduled_execution_to_details(self, mse, context):
        from processes.serializers.missing_scheduled_task_execution_serializer import MissingScheduledTaskExecutionSerializer
        return MissingScheduledTaskExecutionSerializer(mse, context=context).data

    def make_missing_execution_alert(self, mse, alert_method):
        return MissingScheduledTaskExecutionAlert(missing_scheduled_task_execution=mse,
            alert_method=alert_method)

    def alert_summary_template(self):
        return SUMMARY_TEMPLATE
