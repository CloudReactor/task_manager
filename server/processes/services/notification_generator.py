from __future__ import annotations

from typing import Any, TYPE_CHECKING

import logging

from jinja2.sandbox import SandboxedEnvironment

from ..common.notification import *
from ..common.request_helpers import context_with_request
from ..models.user_group_access_level import UserGroupAccessLevel

if TYPE_CHECKING:
    from ..models import (
        RunEnvironment,
        Task, TaskExecution,
        Workflow, WorkflowExecution
    )

logger = logging.getLogger(__name__)


class NotificationGenerator:
    def __init__(self):
        self.sandbox = SandboxedEnvironment()

    def make_template_params(
          self,
          run_environment: RunEnvironment | None = None,
          task: Task | None = None,
          task_execution: TaskExecution | None = None,
          workflow: Workflow | None = None,
          workflow_execution: WorkflowExecution | None = None,
          is_resolution: bool = False,
          severity: str | None = None) -> dict[str, Any]:
        from ..serializers import (
            RunEnvironmentSerializer,
            TaskSerializer,
            TaskExecutionSerializer,
            WorkflowSerializer,
            WorkflowExecutionSerializer,
        )

        if not severity:
            if is_resolution:
                severity = DEFAULT_NOTIFICATION_RESOLUTION_SEVERITY
            else:
                severity = DEFAULT_NOTIFICATION_ERROR_SEVERITY

        template_dict: dict[str, Any] = {
            'severity': severity
        }

        context = context_with_request()

        if workflow_execution:
            template_dict['workflow_execution'] = WorkflowExecutionSerializer(
                    workflow_execution, context=context).data

            workflow = workflow or workflow_execution.workflow

        if workflow:
            template_dict['workflow'] = WorkflowSerializer(
                    workflow, context=context).data
        else:
            template_dict['workflow'] = None

        if task_execution:
            template_dict['task_execution'] = TaskExecutionSerializer(
                    task_execution, context=context).data

            task = task or task_execution.task

        if task:
            template_dict['task'] = TaskSerializer(task,
                    context=context).data

            run_environment = run_environment or task.run_environment
        else:
            template_dict['task'] = None

        if run_environment:
            template_dict['run_environment'] = RunEnvironmentSerializer(
                    run_environment, context=context,
                    forced_access_level=UserGroupAccessLevel.ACCESS_LEVEL_SUPPORT).data
        else:
            template_dict['run_environment'] = None

        return template_dict

    def generate_text(
        self, template_params, template: str | None = None,
        task_execution: TaskExecution | None = None,
        workflow_execution: WorkflowExecution | None = None) -> str:

        if workflow_execution:
            template = template or DEFAULT_NOTIFICATION_WORKFLOW_EXECUTION_SUMMARY_TEMPLATE
        elif task_execution:
            template = template or DEFAULT_NOTIFICATION_TASK_EXECUTION_SUMMARY_TEMPLATE
        elif not template:
            raise ValueError('No template found')

        return self.sandbox.from_string(template).render(template_params)
