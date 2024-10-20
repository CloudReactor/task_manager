import logging

from django.core.management.base import BaseCommand

from proc_wrapper import StatusUpdater

from processes.models import *
from processes.services import *

MIN_CHECK_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate alert methods to notification methods'

    def add_arguments(self, parser):
        #parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        logger.info("Starting notification method migrator ...")

        task_count = 0
        run_env_count = 0
        with StatusUpdater(incremental_count_mode=True) as status_updater:
            for task in Task.objects.all():
                touched = False
                for am in task.alert_methods.all():
                    np = NotificationProfile.objects.filter(uuid=str(am.uuid)).first()

                    if np:
                        task.notification_profiles.add(np)
                        task_count += 1
                        touched = True

                if touched:
                    task.save()

            for run_env in RunEnvironment.objects.all():
                touched = False
                for am in run_env.default_alert_methods.all():
                    np = NotificationProfile.objects.filter(uuid=str(am.uuid)).first()

                    if np:
                        run_env.notification_profiles.add(np)
                        run_env_count += 1
                        touched = True

                if touched:
                    run_env.save()

        msg = f"Finished notification method migrator with {task_count=} {run_env_count=}."
        logger.info(msg)
        status_updater.send_update(last_status_message=msg,
                success_count=(task_count + run_env_count))
