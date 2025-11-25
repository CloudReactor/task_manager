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

    def find_notification_profile_for_alert_method(self, am: AlertMethod) -> NotificationProfile | None:
        np = NotificationProfile.objects.filter(uuid=str(am.uuid)).first()

        if np:
            logger.info(f"Found notification profile {np.uuid} / {np.name} by UUID for alert method {am.uuid}")
        else:
            logger.info(f"Looking up notification profile by name {am.name} for alert method {am.uuid}")
            np = NotificationProfile.objects.filter(name=am.name, created_by_group=am.created_by_group).first()

            if np:
                logger.info(f"Found notification profile {np.uuid} / {np.name} by name for alert method {am.uuid}")
            else:
                logger.warning(f"Could not find notification profile for alert method {am.uuid} / {am.name}")

        return np


    def handle(self, *args, **options):
        logger.info("Starting notification method migrator ...")

        np_count = 0
        task_count = 0
        workflow_count = 0
        run_env_count = 0
        with StatusUpdater(incremental_count_mode=True) as status_updater:
            for am in AlertMethod.objects.all():
                np = NotificationProfile.objects.filter(name=str(am.name),
                      created_by_group=am.created_by_group).first()

                if np:
                    logger.info(f"Found notification profile {np.uuid} / {np.name} for alert method {am.uuid}")
                    continue

                np = NotificationProfile.objects.filter(uuid=str(am.uuid)).first()

                if np is None:
                    np = NotificationProfile(
                        uuid=str(am.uuid),
                        name=am.name,
                        description=am.description,
                        run_environment=am.run_environment,
                        enabled=am.enabled,
                        created_by_user=am.created_by_user,
                        created_by_group=am.created_by_group,
                        created_at=am.created_at,
                        updated_at=am.updated_at,
                    )

                    logger.info(f"Creating notification profile {np.uuid} / {np.name} ...")

                    np.save()
                    np_count += 1

                    logger.info(f"Finished creating notification profile {np.uuid} / {np.name}")

                any_dm_added = False

                am_pagerduty_profile = am.pagerduty_profile
                if am_pagerduty_profile:
                    pd_ndm = PagerDutyNotificationDeliveryMethod.objects.filter(
                        name=am_pagerduty_profile.name,
                        created_by_group=am_pagerduty_profile.created_by_group).first()

                    if pd_ndm:
                        logger.info(f"Found PagerDuty notification delivery method {pd_ndm.uuid} / {pd_ndm.name} for PDP {am_pagerduty_profile.uuid}")
                    else:
                        pd_ndm = PagerDutyNotificationDeliveryMethod.objects.filter(uuid=str(am_pagerduty_profile.uuid)).first()

                        if pd_ndm is None:
                            pd_ndm = PagerDutyNotificationDeliveryMethod(
                                uuid=str(am_pagerduty_profile.uuid),
                                name=am_pagerduty_profile.name,
                                description=am_pagerduty_profile.description,
                                run_environment=am_pagerduty_profile.run_environment,
                                pagerduty_api_key=am_pagerduty_profile.integration_key,
                                pagerduty_event_class_template=am.pagerduty_event_class_template or am_pagerduty_profile.default_event_class_template,
                                pagerduty_event_component_template=am_pagerduty_profile.default_event_component_template,
                                pagerduty_event_group_template=am.pagerduty_event_group_template or am_pagerduty_profile.default_event_group_template,
                                created_by_user=am_pagerduty_profile.created_by_user,
                                created_by_group=am_pagerduty_profile.created_by_group,
                                created_at=am_pagerduty_profile.created_at,
                                updated_at=am_pagerduty_profile.updated_at,
                            )

                            logger.info(f"Creating PagerDuty notification profile {pd_ndm.uuid} / {pd_ndm.name} ...")

                            pd_ndm.save()

                            logger.info(f"Finished creating PagerDuty notification profile {pd_ndm.uuid} / {pd_ndm.name}")

                    np.notification_delivery_methods.add(pd_ndm)
                    any_dm_added = True


                am_email_profile = am.email_notification_profile
                if am_email_profile:
                    email_ndm = EmailNotificationDeliveryMethod.objects.filter(
                        name=am_email_profile.name,
                        created_by_group=am_email_profile.created_by_group).first()

                    if email_ndm:
                        logger.info(f"Found email notification delivery method {email_ndm.uuid} / {email_ndm.name} for EP {am_email_profile.uuid}")
                    else:
                        email_ndm = EmailNotificationDeliveryMethod.objects.filter(uuid=str(am_email_profile.uuid)).first()

                        if email_ndm is None:
                            logger.info(f"Creating email delivery method {am_email_profile.uuid} / {am_email_profile.name}")
                            email_ndm = EmailNotificationDeliveryMethod(
                                uuid=str(am_email_profile.uuid),
                                name=am_email_profile.name,
                                description=am_email_profile.description,
                                run_environment=am_email_profile.run_environment,
                                to_addresses=am_email_profile.to_addresses,
                                cc_addresses=am_email_profile.cc_addresses,
                                bcc_addresses=am_email_profile.bcc_addresses,
                                created_by_user=am_pagerduty_profile.created_by_user,
                                created_by_group=am_pagerduty_profile.created_by_group,
                                created_at=am_pagerduty_profile.created_at,
                                updated_at=am_pagerduty_profile.updated_at,
                            )
                            email_ndm.save()

                    np.notification_delivery_methods.add(email_ndm)
                    any_dm_added = True

                if any_dm_added:
                    np.save()


            for task in Task.objects.all():
                touched = False
                for am in task.alert_methods.all():
                      np = self.find_notification_profile_for_alert_method(am)
                      if np:
                          task.notification_profiles.add(np)
                          task_count += 1
                          touched = True

                if touched:
                    task.save()

            for workflow in Workflow.objects.all():
                touched = False
                for am in workflow.alert_methods.all():
                      np = self.find_notification_profile_for_alert_method(am)
                      if np:
                          workflow.notification_profiles.add(np)
                          workflow_count += 1
                          touched = True

                if touched:
                    workflow.save()

            for run_env in RunEnvironment.objects.all():
                touched = False
                for am in run_env.default_alert_methods.all():
                    np = self.find_notification_profile_for_alert_method(am)

                    if np:
                        run_env.notification_profiles.add(np)
                        run_env_count += 1
                        touched = True

                if touched:
                    run_env.save()

        msg = f"Finished notification method migrator with {task_count=} {workflow_count=} {run_env_count=}."
        logger.info(msg)
        status_updater.send_update(last_status_message=msg,
                success_count=(task_count + workflow_count + run_env_count))
