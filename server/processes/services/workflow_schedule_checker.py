from typing import override

from datetime import datetime
import logging

from django.db.models import Manager

from ..models import *
from .schedule_checker import ScheduleChecker


logger = logging.getLogger(__name__)


class WorkflowScheduleChecker(ScheduleChecker[Workflow, WorkflowExecution]):
    @override
    def model_name(self) -> str:
        return 'Workflow'

    @override
    def manager(self) -> Manager[Workflow]:
        return Workflow.objects

    @override
    def make_missing_scheduled_execution_event(self, schedulable: Workflow,
            expected_execution_at: datetime, missing_execution_count: int) -> MissingScheduledWorkflowExecutionEvent:
        return MissingScheduledWorkflowExecutionEvent(
                created_by_group=schedulable.created_by_group,
                run_environment=schedulable.run_environment,
                workflow=schedulable,
                schedule=schedulable.schedule,
                expected_execution_at=expected_execution_at,
                missing_execution_count=missing_execution_count)
