import logging
import os

from django.db.models import Q
from django.core.management.base import BaseCommand

from proc_wrapper import StatusUpdater

from processes.models import RunEnvironment
from processes.models.convert_legacy_em_and_infra import (
    populate_run_environment_infra,
    populate_run_environment_aws_ecs_configuration
)


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Converts Run Environments created with legacy schema to new schema'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        logger.info("Starting Run Environment config conversion ...")

        with StatusUpdater() as status_updater:
            should_reset = (os.getenv('TASK_MANAGER_SHOULD_RESET', 'FALSE') == 'TRUE')

            logger.info(f"{should_reset=}")

            qs = RunEnvironment.objects.exclude(aws_ecs_default_execution_role='')

            if not should_reset:
                qs = qs.filter(Q(aws_settings__isnull=True) | Q(default_aws_ecs_configuration__isnull=True))

            success_count = 0
            error_count = 0
            for run_env in qs.all():
                changed = False
                try:
                    if should_reset or (run_env.aws_settings is None):
                        changed = populate_run_environment_infra(run_environment=run_env)

                    if should_reset or (run_env.default_aws_ecs_configuration is None):
                        changed = populate_run_environment_aws_ecs_configuration(
                                run_environment=run_env) or changed
                except Exception:
                    msg = f"Failed to convert Run Environment {run_env.uuid=} {run_env.name=}"
                    logger.exception(msg)
                    error_count += 1
                    status_updater.send_update(last_status_message=msg,
                        error_count=error_count)
                else:
                    if changed:
                        run_env.save()
                        success_count += 1

            status_updater.send_update(success_count=success_count)

            logger.info(f"Migrated {success_count} Run Environments successfully with {error_count} errors")
