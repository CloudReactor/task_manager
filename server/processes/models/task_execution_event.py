from django.db import models

from ..common.utils import strip_prefix_before_last_dot
from .task_event import TaskEvent


class TaskExecutionEvent(TaskEvent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.task_execution:
            self.task = self.task or self.task_execution.task

            if not self.run_environment:
                self.run_environment = self.task_execution.run_environment

            if not self.created_by_group:
                self.created_by_group = self.task_execution.created_by_group    

        if self.task:
            if not self.created_by_group:
                self.created_by_group = self.task.created_by_group

            if not self.run_environment:
                self.run_environment = self.task.run_environment

            if not self.created_by_group:
                self.created_by_group = self.task.created_by_group

        if self.run_environment:
            if not self.created_by_group:
                self.created_by_group = self.run_environment.created_by_group


    def __str__(self) -> str:
        te_id = str(self.task_execution.uuid) if self.task_execution else '[REMOVED]'
        return strip_prefix_before_last_dot(self.type) + ' TaskExec ' + te_id \
                + ' / ' + str(self.uuid)
