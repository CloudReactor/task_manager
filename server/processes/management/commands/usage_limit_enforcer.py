from typing import List

import logging

from django.core.management.base import BaseCommand

from proc_wrapper import StatusUpdater

from processes.models import (
  Task,
  Workflow
)
from processes.services import *

MIN_CHECK_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ensure usage limits are applied'

    def add_arguments(self, parser):
        #parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        logger.info('Starting usage limit enforcer ...')

        exceptions: List[Exception] = []

        with StatusUpdater(incremental_count_mode=True) as status_updater:
            try:
                self.enforce_task_execution_limits(status_updater)
            except Exception as ex:
                logger.exception('Failed enforcing Task Execution limits')
                exceptions.append(ex)

            try:
                self.enforce_workflow_execution_limits(status_updater)
            except Exception as ex:
                logger.exception('Failed enforcing Workflow Execution limits')
                exceptions.append(ex)

        if len(exceptions) > 0:
            raise exceptions[0]

        logger.info('Usage limit enforcer succeeded')

    def enforce_task_execution_limits(self, status_updater: StatusUpdater) -> int:
        total_purged_count = 0
        for task in Task.objects.select_related('created_by_group').iterator():
            try:
                purged_count = task.purge_history()
                total_purged_count += purged_count
                status_updater.send_update(success_count=purged_count)
            except:
                logger.exception(f'Failed enforcing Task Execution limits on Task {task.uuid}')
                status_updater.send_update(error_count=1)

        logger.info(f'Purged a total of {total_purged_count} Task Executions')

        return total_purged_count

    def enforce_workflow_execution_limits(self,
            status_updater: StatusUpdater) -> int:
        total_purged_count = 0
        for workflow in Workflow.objects.select_related('created_by_group').iterator():
            try:
                purged_count = workflow.purge_history()
                total_purged_count += purged_count
                status_updater.send_update(success_count=purged_count)
            except:
                logger.exception(f'Failed enforcing Workflow Execution limits on Workflow {workflow.uuid}')
                status_updater.send_update(error_count=1)

        logger.info(f'Purged a total of {total_purged_count} Workflow Executions')

        return total_purged_count