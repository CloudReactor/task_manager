import logging
import os

from django.core.management.base import BaseCommand

from proc_wrapper import StatusUpdater

from processes.execution_methods import AwsEcsExecutionMethod
from processes.models import Task

MIN_CHECK_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sets is_xxx_managed flags on current Tasks'

    def add_arguments(self, parser):
        #parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        logger.info("Starting Task flag setting ...")

        with StatusUpdater() as status_updater:
            should_reset = (os.getenv('TASK_MANAGER_SHOULD_RESET_MANAGED_FLAGS', 'FALSE') == 'TRUE')

            logger.info(f"{should_reset=}")

            success_count = 0
            error_count = 0
            for task in Task.objects.all():
                emt = task.execution_method_type
                manageable = (not task.was_auto_created) and (emt == AwsEcsExecutionMethod.NAME)
                try:
                    if should_reset or (task.is_scheduling_managed is None):
                        if task.schedule:
                            task.is_scheduling_managed = manageable
                        else:
                            task.is_scheduling_managed = None

                    if should_reset or (task.is_service_managed is None):
                        if task.service_instance_count:
                            task.is_service_managed = manageable
                        else:
                            task.is_service_managed = None

                    task.save()
                except Exception:
                    msg = f"Failed to set managed flags on Task {task.uuid=} {task.name=}"
                    logger.exception(msg)
                    error_count += 1
                    status_updater.send_update(last_status_message=msg,
                        error_count=error_count)
                else:
                    success_count += 1

        status_updater.send_update(success_count=success_count)

        logger.info(f"Set managed flags on {success_count} Tasks successfully with {error_count} errors")