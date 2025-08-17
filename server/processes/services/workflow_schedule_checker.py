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
    def missing_scheduled_executions_of(self, schedulable: Workflow) -> Manager[MissingScheduledWorkflowExecutionEvent]:
        return MissingScheduledWorkflowExecutionEvent.objects.filter(
                workflow=schedulable, resolved_at__isnull=True)

    @override
    def executions_of(self, schedulable: Workflow) -> Manager[WorkflowExecution]:
        return WorkflowExecution.objects.filter(workflow=schedulable)

    @override
    def make_missing_scheduled_execution_event(self, schedulable: Workflow,
            expected_execution_at: datetime) -> MissingScheduledWorkflowExecutionEvent:
        return MissingScheduledWorkflowExecutionEvent(workflow=schedulable,
                schedule=schedulable.schedule,
                expected_execution_at=expected_execution_at)
