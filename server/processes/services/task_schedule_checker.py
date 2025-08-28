from typing import override
from datetime import datetime
import logging

from django.db.models import Manager, Q

from ..models import *

from .schedule_checker import ScheduleChecker


logger = logging.getLogger(__name__)


class TaskScheduleChecker(ScheduleChecker[Task, TaskExecution]):
    @override
    def model_name(self) -> str:
        return 'Task'

    @override
    def manager(self) -> Manager[Task]:
        return Task.objects.filter(Q(managed_probability__gte=1.0) |
                Q(managed_probability__isnull=True))

    @override
    def missing_scheduled_executions_of(self, schedulable: Task) -> Manager[MissingScheduledTaskExecutionEvent]:
        return MissingScheduledTaskExecutionEvent.objects.filter(task=schedulable,
                resolved_at__isnull=True)

    @override
    def executions_of(self, schedulable: Task) -> Manager[TaskExecution]:
        return TaskExecution.objects.filter(task=schedulable)

    @override
    def make_missing_scheduled_execution_event(self, schedulable: Task,
            expected_execution_at: datetime) -> MissingScheduledTaskExecutionEvent:
        return MissingScheduledTaskExecutionEvent(task=schedulable,
            schedule=schedulable.schedule, expected_execution_at=expected_execution_at)
