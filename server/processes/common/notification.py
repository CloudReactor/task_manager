NOTIFICATION_SEVERITIES = ['critical', 'error', 'warning', 'info']
NOTIFICATION_SEVERITY_CHOICES = [(x, x) for x in NOTIFICATION_SEVERITIES]
DEFAULT_NOTIFICATION_SUCCESS_SEVERITY = 'info'
DEFAULT_NOTIFICATION_ERROR_SEVERITY = 'error'
DEFAULT_NOTIFICATION_RESOLUTION_SEVERITY = 'info'

DEFAULT_NOTIFICATION_SOURCE = 'CloudReactor'

DEFAULT_NOTIFICATION_WORKFLOW_EXECUTION_SUMMARY_TEMPLATE = \
    """Workflow '{{workflow_execution.workflow.name}}' finished with status {{workflow_execution.status}}"""
DEFAULT_NOTIFICATION_TASK_EXECUTION_SUMMARY_TEMPLATE = \
    """Task '{{task.name}}' finished with status {{task_execution.status}}"""
