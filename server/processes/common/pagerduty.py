from processes.common.notification import *

PAGERDUTY_EVENT_SEVERITIES = ['critical', 'error', 'warning', 'info']
PAGERDUTY_EVENT_SEVERITY_CHOICES = [(x, x) for x in PAGERDUTY_EVENT_SEVERITIES]
DEFAULT_PAGERDUTY_EVENT_SUCCESS_SEVERITY = DEFAULT_NOTIFICATION_SUCCESS_SEVERITY
DEFAULT_PAGERDUTY_EVENT_ERROR_SEVERITY = DEFAULT_NOTIFICATION_RESOLUTION_SEVERITY

DEFAULT_PAGERDUTY_EVENT_SOURCE = DEFAULT_NOTIFICATION_SOURCE
DEFAULT_PAGERDUTY_EVENT_ERROR_SEVERITY = DEFAULT_PAGERDUTY_EVENT_SUCCESS_SEVERITY
DEFAULT_PAGERDUTY_EVENT_RESOLUTION_SEVERITY = DEFAULT_NOTIFICATION_RESOLUTION_SEVERITY
DEFAULT_PAGERDUTY_EVENT_WORKFLOW_EXECUTION_SUMMARY_TEMPLATE = DEFAULT_NOTIFICATION_WORKFLOW_EXECUTION_SUMMARY_TEMPLATE
DEFAULT_PAGERDUTY_EVENT_TASK_EXECUTION_SUMMARY_TEMPLATE = DEFAULT_NOTIFICATION_TASK_EXECUTION_SUMMARY_TEMPLATE
