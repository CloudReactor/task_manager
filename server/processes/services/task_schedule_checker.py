from typing import cast
from datetime import datetime
import logging

from processes.models import *
from .schedule_checker import ScheduleChecker

SUMMARY_TEMPLATE = \
    """Task '{{task.name}}' did not execute as scheduled at {{expected_execution_at}}"""

logger = logging.getLogger(__name__)


class TaskScheduleChecker(ScheduleChecker[Task]):
    def model_name(self) -> str:
        return 'Task'

    def manager(self):
        return Task.objects

    def missing_scheduled_executions_of(self, schedulable: Task):
        return MissingScheduledTaskExecution.objects.filter(task=schedulable)

    def executions_of(self, schedulable: Task):
        return TaskExecution.objects.filter(
                task=cast(Task, schedulable))

    def make_missing_scheduled_execution(self, schedulable: Task,
            expected_execution_at: datetime) -> MissingScheduledTaskExecution:
        return MissingScheduledTaskExecution(task=schedulable,
            schedule=schedulable.schedule, expected_execution_at=expected_execution_at)

    def missing_scheduled_execution_to_details(self,
            mse: MissingScheduledExecution, context) -> dict:
        from ..serializers.missing_scheduled_task_execution_serializer import (
            MissingScheduledTaskExecutionSerializer
        )
        return MissingScheduledTaskExecutionSerializer(mse, context=context).data

    def make_missing_execution_alert(self,
            mse: MissingScheduledExecution,
            alert_method: AlertMethod) -> MissingScheduledTaskExecutionAlert:
        return MissingScheduledTaskExecutionAlert(
                missing_scheduled_task_execution=cast(
                        MissingScheduledTaskExecution, mse),
                alert_method=alert_method)

    def alert_summary_template(self) -> str:
        return SUMMARY_TEMPLATE
