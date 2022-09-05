import logging
import os

from django.core.management.base import BaseCommand

from proc_wrapper import StatusUpdater

from processes.execution_methods import AwsEcsExecutionMethod
from processes.models import Task
from processes.models.convert_legacy_em_and_infra import populate_task_emc_and_infra


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Converts Tasks created with legacy execution method schema to new schema'

    def add_arguments(self, parser):
        #parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        logger.info("Starting Task execution method conversion ...")

        with StatusUpdater() as status_updater:
            should_reset = (os.getenv('TASK_MANAGER_SHOULD_RESET_EMCD', 'FALSE') == 'TRUE')

            logger.info(f"{should_reset=}")

            qs = Task.objects.filter(execution_method_type=AwsEcsExecutionMethod.NAME)

            if not should_reset:
                qs = qs.filter(execution_method_capability_details__isnull=True)

            success_count = 0
            error_count = 0
            for task in qs.all():
                try:
                    if populate_task_emc_and_infra(task=task):
                        task.enrich_settings()
                        task.save()
                except Exception:
                    msg = f"Failed to convert Task {task.uuid=} {task.name=}"
                    logger.exception(msg)
                    error_count += 1
                    status_updater.send_update(last_status_message=msg,
                        error_count=error_count)
                else:
                    success_count += 1

            status_updater.send_update(success_count=success_count)

            logger.info(f"Migrated {success_count} Tasks successfully with {error_count} errors")