import logging
import os

from django.core.paginator import Paginator
from django.core.management.base import BaseCommand

from proc_wrapper import StatusUpdater

from processes.models import TaskExecution
from processes.models.convert_legacy_em_and_infra import (
    populate_task_execution_em_and_infra
)


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Converts Task Executions created with legacy execution method schema to new schema'

    def add_arguments(self, parser):
        #parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        logger.info("Starting Task Execution execution method conversion ...")

        with StatusUpdater() as status_updater:
            should_reset = (os.getenv('TASK_MANAGER_SHOULD_RESET', 'FALSE') == 'TRUE')

            logger.info(f"{should_reset=}")

            qs = TaskExecution.objects.filter(aws_ecs_task_definition_arn__isnull=False)

            success_count = 0
            error_count = 0

            paginator = Paginator(qs.all(), 1000)

            for page_idx in range(1, paginator.num_pages+1):
                for task_execution in paginator.page(page_idx).object_list:
                    try:
                        if populate_task_execution_em_and_infra(
                                task_execution=task_execution,
                                should_reset=should_reset):
                            task_execution.enrich_settings()
                            task_execution.save()
                    except Exception:
                        msg = f"Failed to convert Task Execution {task_execution.uuid=}"
                        logger.exception(msg)
                        error_count += 1
                        status_updater.send_update(last_status_message=msg,
                            error_count=error_count)
                    else:
                        success_count += 1

                status_updater.send_update(success_count=success_count)

            logger.info(f"Migrated {success_count} Task Executions successfully with {error_count} errors")
