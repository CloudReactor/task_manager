from typing import override
from datetime import datetime
import logging

from django.db.models import Manager

from ..models import *

from .schedule_checker import ScheduleChecker


logger = logging.getLogger(__name__)


class TaskScheduleChecker(ScheduleChecker[Task, TaskExecution]):
    @override
    def model_name(self) -> str:
        return 'Task'

    @override
    def manager(self) -> Manager[Task]:
        return Task.objects

    @override
    def make_missing_scheduled_execution_event(self, schedulable: Task,
            expected_execution_at: datetime, missing_execution_count: int) -> MissingScheduledTaskExecutionEvent:
        return MissingScheduledTaskExecutionEvent(
            created_by_group=schedulable.created_by_group,
            run_environment=schedulable.run_environment,
            task=schedulable,
            schedule=schedulable.schedule, expected_execution_at=expected_execution_at,
            missing_execution_count=missing_execution_count)
