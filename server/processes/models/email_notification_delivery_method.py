import logging

from typing import Any, Optional, cast

from django.db import models
from django.conf import settings
from django.core.mail import EmailMessage

from django.contrib.postgres.fields import ArrayField

from templated_email import get_templated_mail

from ..common.notification import *
from .event import Event
from .notification_delivery_method import NotificationDeliveryMethod
from .task_execution_status_change_event import TaskExecutionStatusChangeEvent
from .workflow_execution_status_change_event import WorkflowExecutionStatusChangeEvent

logger = logging.getLogger(__name__)


class EmailNotificationDeliveryMethod(NotificationDeliveryMethod):
    DEFAULT_REPLY_TO_EMAIL_ADDRESS = 'no-reply@cloudreactor.io'

    email_to_addresses = ArrayField(models.EmailField(max_length=1000, blank=False), blank=True, null=True)
    email_cc_addresses = ArrayField(models.EmailField(max_length=1000, blank=False), blank=True, null=True)
    email_bcc_addresses = ArrayField(models.EmailField(max_length=1000, blank=False), blank=True, null=True)

    def send(self, event: Event) -> Optional[dict[str, Any]]:
        if isinstance(event, TaskExecutionStatusChangeEvent):
            email = self.make_task_execution_status_change_email(cast(TaskExecutionStatusChangeEvent, event))
        elif isinstance(event, WorkflowExecutionStatusChangeEvent):
            email = self.make_workflow_execution_status_change_email(cast(WorkflowExecutionStatusChangeEvent, event))
        else:
            email = EmailMessage(
                  subject=event.error_summary,
                  body=event.error_details_message or event.error_summary,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  to=self.email_to_addresses or [],
                  cc=self.email_cc_addresses or [],
                  bcc=self.email_bcc_addresses or [],
                  reply_to=[settings.ENVIRON('DJANGO_EMAIL_REPLY_TO',
                          default='no-reply@cloudreactor.io')])

        logger.info(f"Sending email to {self.email_to_addresses} ...")
        success_count = email.send()
        logger.info(f"Done sending email to {self.email_to_addresses}, {success_count=}.")

        return {
          'success_count': success_count
        }

    def make_task_execution_status_change_email(self, event: TaskExecutionStatusChangeEvent) -> Any:
        from ..services import NotificationGenerator

        notification_generator = NotificationGenerator()

        template_params = notification_generator.make_template_params(
            task_execution=event.task_execution,
            severity=event.severity_label)

        template_params['model_task_execution'] = event.task_execution
        template_params['event'] = event

        if event.details:
            template_params.update(event.details)

        email = get_templated_mail(
                template_name='task_execution_status',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=self.email_to_addresses or [],
                cc=self.email_cc_addresses or [],
                bcc=self.email_bcc_addresses or [],
                context=template_params,
        )

        email.reply_to = [settings.ENVIRON('DJANGO_EMAIL_REPLY_TO',
                default=self.DEFAULT_REPLY_TO_EMAIL_ADDRESS)]

        return email

    def make_workflow_execution_status_change_email(self, event: WorkflowExecutionStatusChangeEvent) -> Any:
        from ..services import NotificationGenerator

        notification_generator = NotificationGenerator()

        template_params = notification_generator.make_template_params(
            workflow_execution=event.workflow_execution,
            severity=event.severity_label)

        template_params['model_workflow_execution'] = event.workflow_execution
        template_params['event'] = event

        if event.details:
            template_params.update(event.details)

        email = get_templated_mail(
                template_name='workflow_execution_status',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=self.email_to_addresses or [],
                cc=self.email_cc_addresses or [],
                bcc=self.email_bcc_addresses or [],
                context=template_params,
        )

        email.reply_to = [settings.ENVIRON('DJANGO_EMAIL_REPLY_TO',
                default=self.DEFAULT_REPLY_TO_EMAIL_ADDRESS)]

        return email
