import logging
import sys
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from proc_wrapper import StatusUpdater

from processes.services import *

MIN_CHECK_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ensure Tasks and Workflows are run on schedule'

    def add_arguments(self, parser):
        #parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        logger.info("Starting check loop ...")

        with StatusUpdater(incremental_count_mode=True) as status_updater:
            while True:
                attempt_count = 0
                success_count = 0
                failure_count = 0

                last_start_time = timezone.now()
                total_run_duration = 0

                attempt_count += 1
                try:
                    ServiceConcurrencyChecker().check_all()
                    success_count += 1
                except Exception:
                    failure_count += 1
                    msg = 'ServiceConcurrencyChecker failed'
                    logger.exception(msg)
                    status_updater.send_update(last_status_message=msg,
                            success_count=success_count,
                            failure_count=failure_count)

                current_time = timezone.now()
                run_duration = int((current_time - last_start_time).total_seconds())
                total_run_duration += run_duration

                logger.info(f"Checking all services took {run_duration} seconds")

                attempt_count += 1
                try:
                    TaskScheduleChecker().check_all()
                    success_count += 1
                except Exception:
                    failure_count += 1
                    msg = 'TaskScheduleChecker failed'
                    logger.exception(msg)
                    status_updater.send_update(last_status_message=msg,
                            success_count=success_count,
                            failure_count=failure_count)

                current_time = timezone.now()
                run_duration = int((current_time - last_start_time).total_seconds())
                total_run_duration += run_duration

                logger.info(f"Checking all Task schedules took {run_duration} seconds")

                attempt_count += 1
                try:
                    WorkflowScheduleChecker().check_all()
                    success_count += 1
                except Exception:
                    failure_count += 1
                    msg = 'WorkflowScheduleChecker failed'
                    logger.exception(msg)
                    status_updater.send_update(last_status_message=msg,
                            success_count=success_count,
                            failure_count=failure_count)

                current_time = timezone.now()
                run_duration = int((current_time - last_start_time).total_seconds())
                total_run_duration += run_duration

                logger.info(f"Checking all Workflow schedules took {run_duration} seconds")

                attempt_count += 1
                try:
                    TaskExecutionChecker().check_all()
                    success_count += 1
                except Exception:
                    failure_count += 1
                    msg = 'TaskExecutionChecker failed'
                    logger.exception(msg)
                    status_updater.send_update(last_status_message=msg,
                            success_count=success_count,
                            failure_count=failure_count)

                current_time = timezone.now()
                run_duration = int((current_time - last_start_time).total_seconds())
                total_run_duration += run_duration

                logger.info(f"Checking all Task Executions took {run_duration} seconds")

                attempt_count += 1
                try:
                    WorkflowExecutionChecker().check_all()
                    success_count += 1
                except Exception:
                    failure_count += 1
                    msg = 'WorkflowExecutionChecker failed'
                    logger.exception(msg)
                    status_updater.send_update(last_status_message=msg,
                            success_count=success_count,
                            failure_count=failure_count)

                current_time = timezone.now()
                run_duration = int((current_time - last_start_time).total_seconds())
                total_run_duration += run_duration

                logger.info(f"Checking all Workflow Executions took {run_duration} seconds")


                try:
                    PostponedEventChecker().check_all()
                    success_count += 1
                except Exception:
                    failure_count += 1
                    msg = 'PostponedEventChecker failed'
                    logger.exception(msg)
                    status_updater.send_update(last_status_message=msg,
                            success_count=success_count,
                            failure_count=failure_count)

                if failure_count == attempt_count:
                    msg = 'All checks failed to execute, exiting'
                    logger.error(msg)
                    status_updater.send_update(last_status_message=msg,
                            success_count=success_count,
                            failure_count=failure_count)
                    sys.exit(-1)

                sleep_seconds = MIN_CHECK_INTERVAL_SECONDS - total_run_duration

                if sleep_seconds > 0:
                    logger.debug(f"Sleeping for {sleep_seconds} seconds ...")
                    time.sleep(sleep_seconds)
