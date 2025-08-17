from typing import TYPE_CHECKING

from django.db import models

from ..common.utils import strip_prefix_before_last_dot
from .task_event import TaskEvent


class TaskExecutionEvent(TaskEvent):
    task_execution = models.ForeignKey('TaskExecution', null=True, on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.task_execution and not self.task:
            self.task = self.task_execution.task

        if self.task and not self.created_by_group:
            self.created_by_group = self.task.created_by_group


    def __str__(self) -> str:
        te_id = str(self.task_execution.uuid) if self.task_execution else '[REMOVED]'
        return strip_prefix_before_last_dot(self.type) + ' TaskExec ' + te_id \
                + ' / ' + str(self.uuid)
