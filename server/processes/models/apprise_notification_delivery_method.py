from __future__ import annotations

from typing import Any

import logging

from django.conf import settings
from django.db import models

import apprise

from ..common.notification import *
from .event import Event
from .notification_delivery_method import NotificationDeliveryMethod

logger = logging.getLogger(__name__)


class AppriseNotificationDeliveryMethod(NotificationDeliveryMethod):
    """
    Notification delivery method using the Apprise library.

    Apprise supports multiple notification services including:
    - Email (SMTP)
    - Slack
    - Discord
    - Microsoft Teams
    - Telegram
    - Twilio (SMS)
    - PushBullet
    - Pushover
    - IFTTT
    - And many more

    The apprise_url field contains a service URL that Apprise
    can send notifications to.
    """

    apprise_url = models.CharField(
        max_length=2000,
        null=True,
        blank=False,
        help_text="URL for an Apprise notification service (e.g., 'slack://xoxb-token-here/C123456/U123456'). May contain placeholders in braces (e.g., '{token}')."
    )

    @staticmethod
    def get_apprise_asset() -> apprise.AppriseAsset:
        """
        Get the global Apprise asset configuration.
        This identifies the application and provides branding for all notifications.
        """

        apprise_settings = settings.APPRISE_SETTINGS
        return apprise.AppriseAsset(
            app_id=apprise_settings['APP_ID'],
            app_desc=apprise_settings['APP_DESC'],
            app_url=apprise_settings['APP_URL'],
        )

    def send(self, event: Event) -> dict[str, Any] | None:
        """
        Send notification via Apprise to configured services.

        Returns a dict with:
        - 'success': Number of services successfully notified
        - 'notification_type': The type of notification sent
        """
        from .task_execution_status_change_event import TaskExecutionStatusChangeEvent
        from .workflow_execution_status_change_event import WorkflowExecutionStatusChangeEvent

        if not self.apprise_url:
            raise ValueError("Apprise URL is required for Apprise notifications")

        # Create Apprise instance with global asset configuration
        apobj = apprise.Apprise(asset=self.get_apprise_asset())

        if not apobj.add(self.apprise_url):
            raise ValueError(f"Invalid Apprise URL: {self.apprise_url}")

        # Build notification body
        title = event.error_summary or "CloudReactor Notification"
        body = event.error_details_message or event.error_summary or "Event notification"

        # Add event severity information
        severity_label = getattr(event, 'severity_label', None)
        if severity_label:
            title = f"[{severity_label.upper()}] {title}"

        # # Add task/workflow execution details if available
        # if event.hasattr('task') and event.task:
        #     body = f"Task: {task_execution.name}\n\" \
        #     task_event = cast(TaskExecutionStatusChangeEvent, event)
        #     if task_event.task_execution:
        #         task_execution: TaskExecution = task_event.task_execution
        #         body = f"Task: {task_execution.name}\n" \
        #                f"Status: {task_execution.status}\n" \
        #                f"UUID: {task_execution.uuid}\n\n{body}"
        # elif isinstance(event, WorkflowExecutionStatusChangeEvent):
        #     workflow_event = cast(WorkflowExecutionStatusChangeEvent, event)
        #     if workflow_event.workflow_execution:
        #         workflow_execution = workflow_event.workflow_execution
        #         body = f"Workflow: {workflow_execution.name}\n" \
        #                f"Status: {workflow_execution.status}\n" \
        #                f"UUID: {workflow_execution.uuid}\n\n{body}"

        # Map event severity to Apprise notification type
        # Apprise supports: info, success, warning, failure
        notify_type = self._compute_apprise_notification_type(event.severity)

        logger.info(f"Sending Apprise notification to '{self.apprise_url}' ...")

        try:
            # Send notification
            success = apobj.notify(
                body=body,
                title=title,
                notify_type=notify_type,
                body_format=apprise.NotifyFormat.HTML,
            )

            logger.info(f"Done sending Apprise notification, {success=}.")

            return {
                'success': success,
            }
        except Exception as e:
            logger.error(f"Error sending Apprise notification: {e}", exc_info=True)
            raise

    def _compute_apprise_notification_type(self, severity: int) -> str:
        """
        Map event severity to Apprise notification type.

        Apprise notification types:
        - info: informational
        - success: successful operation
        - warning: warning message
        - failure: critical failure
        """
        if severity >= Event.Severity.CRITICAL:
            return apprise.NotifyType.FAILURE
        elif severity >= Event.Severity.ERROR:
            return apprise.NotifyType.FAILURE
        elif severity >= Event.Severity.WARNING:
            return apprise.NotifyType.WARNING
        else:
            return apprise.NotifyType.INFO
