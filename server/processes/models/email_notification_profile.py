import logging

from typing import Any, Dict, Optional

from django.db import models
from django.conf import settings
from django.core.mail import EmailMessage

from django.contrib.postgres.fields import ArrayField

from templated_email import get_templated_mail

from ..common.notification import *
from .named_with_uuid_and_run_environment_model import NamedWithUuidAndRunEnvironmentModel
from .task_execution import TaskExecution
from .workflow_execution import WorkflowExecution


logger = logging.getLogger(__name__)


class EmailNotificationProfile(NamedWithUuidAndRunEnvironmentModel):
    DEFAULT_EMAIL_NOTIFICATION_TASK_EXECUTION_SUBJECT_TEMPLATE = \
        DEFAULT_NOTIFICATION_TASK_EXECUTION_SUMMARY_TEMPLATE

    DEFAULT_EMAIL_NOTIFICATION_WORKFLOW_EXECUTION_SUBJECT_TEMPLATE = \
        DEFAULT_NOTIFICATION_WORKFLOW_EXECUTION_SUMMARY_TEMPLATE

    # TODO: improve these
    DEFAULT_EMAIL_NOTIFICATION_TASK_EXECUTION_BODY_TEMPLATE = \
        DEFAULT_NOTIFICATION_TASK_EXECUTION_SUMMARY_TEMPLATE

    DEFAULT_EMAIL_NOTIFICATION_WORKFLOW_EXECUTION_BODY_TEMPLATE = \
        DEFAULT_NOTIFICATION_WORKFLOW_EXECUTION_SUMMARY_TEMPLATE

    class Meta:
        unique_together = (('name', 'created_by_group'),)

    to_addresses = ArrayField(models.EmailField(max_length=1000, blank=False), blank=True, null=True)
    cc_addresses = ArrayField(models.EmailField(max_length=1000, blank=False), blank=True, null=True)
    bcc_addresses = ArrayField(models.EmailField(max_length=1000, blank=False), blank=True, null=True)
    subject_template = models.CharField(max_length=1000, blank=True)
    body_template = models.CharField(max_length=10000, blank=True)

    def send(self, details: Optional[Dict[str, Any]] = None, severity: Optional[str] = None,
             subject_template: Optional[str] = None,
             body_template: Optional[str] = None,
             template_name: Optional[str] = None,
             task_execution: Optional[TaskExecution] = None,
             workflow_execution: Optional[WorkflowExecution] = None,
             is_resolution: bool = False):
        from processes.services import NotificationGenerator

        notification_generator = NotificationGenerator()

        template_params = notification_generator.make_template_params(
            task_execution=task_execution,
            workflow_execution=workflow_execution,
            is_resolution=is_resolution,
            severity=severity)

        if details:
            template_params.update(details)

        if (body_template is None) and (template_name is None):
            if task_execution:
                template_name = 'task_execution_status'
                template_params['model_task_execution'] = task_execution

            if workflow_execution:
                template_name = 'workflow_execution_status'
                template_params['model_workflow_execution'] = workflow_execution

            if template_name is None:
                body_template = subject_template or ''

        if body_template:
            if not subject_template:
                if workflow_execution:
                    subject_template = self.DEFAULT_EMAIL_NOTIFICATION_WORKFLOW_EXECUTION_SUBJECT_TEMPLATE
                elif task_execution:
                    subject_template = self.DEFAULT_EMAIL_NOTIFICATION_TASK_EXECUTION_SUBJECT_TEMPLATE

            subject = notification_generator.generate_text(
                template_params=template_params,
                template=subject_template or 'CloudReactor Notification',
                task_execution=task_execution,
                workflow_execution=workflow_execution,
                is_resolution=is_resolution)

            body = notification_generator.generate_text(
                template_params=template_params,
                template=body_template,
                task_execution=task_execution,
                workflow_execution=workflow_execution,
                is_resolution=is_resolution)

            email = EmailMessage(
                  subject=subject,
                  body=body,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  to=self.to_addresses or [],
                  cc=self.cc_addresses or [],
                  bcc=self.bcc_addresses or [],
                  reply_to=[settings.ENVIRON('DJANGO_EMAIL_REPLY_TO',
                          default='no-reply@cloudreactor.io')])
        else:
            if not template_name:
                raise ValueError('Unknown template')

            email = get_templated_mail(
                    template_name=template_name,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=self.to_addresses or [],
                    cc=self.cc_addresses or [],
                    bcc=self.bcc_addresses or [],
                    context=template_params,
            )

            email.reply_to = [settings.ENVIRON('DJANGO_EMAIL_REPLY_TO',
                    default='no-reply@cloudreactor.io')]

        logger.info(f"Sending email to {self.to_addresses} ...")
        email.send()
        logger.info(f"Done sending email to {self.to_addresses}.")
