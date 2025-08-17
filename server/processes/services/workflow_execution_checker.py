import logging

from django.db import transaction
from django.utils import timezone

from ..models import WorkflowExecution

logger = logging.getLogger(__name__)


class WorkflowExecutionChecker:
    def check_all(self) -> None:
        # TODO: optimize query to only fetch problematic executions
        for we in WorkflowExecution.objects.select_related(
                'workflow').filter(status__in=WorkflowExecution.IN_PROGRESS_STATUSES):
            try:
                self.check_workflow_execution(we)
            except Exception:
                logger.exception(f"Failed checking Workflow Execution {we.uuid} of Workflow {we.workflow}")

    def check_workflow_execution(self, we: WorkflowExecution) -> None:
        if we.finished_at:
            logger.error(f"Workflow Execution {we.uuid} has an in progress status but finished_at is not NULL")
            return

        with transaction.atomic():
            we.refresh_from_db()

            if we.status in WorkflowExecution.IN_PROGRESS_STATUSES:
                if self.check_timeout(we):
                    return

    def check_timeout(self, we: WorkflowExecution) -> bool:
        workflow = we.workflow
        utc_now = timezone.now()
        run_duration = (utc_now - (we.started_at or we.created_at)).total_seconds()

        if workflow.max_age_seconds is not None:
            logger.debug(f"Run duration of Workflow Execution {we.uuid} is {run_duration} seconds")
            if run_duration > workflow.max_age_seconds:
                logger.info(
                    f"Run duration of Workflow Execution {we.uuid} {run_duration} seconds > max age {workflow.max_age_seconds} seconds, stopping")
                we.handle_timeout()
                return True

            logger.debug(f"Run duration of Workflow Execution {we.uuid} is within max age")

        return False
