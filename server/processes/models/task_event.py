from __future__ import annotations

from typing import TYPE_CHECKING, override

from django.db import models

from ..common.utils import strip_prefix_before_last_dot
from .schedulable_instance_event import SchedulableInstanceEvent


if TYPE_CHECKING:
    from .task import Task


class TaskEvent(SchedulableInstanceEvent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.task and not self.created_by_group:
            self.created_by_group = self.task.created_by_group


    def __str__(self) -> str:
        task_id = str(self.task.uuid) if self.task else '[REMOVED]'
        return strip_prefix_before_last_dot(self.type) + ' Task ' + task_id \
                + ' / ' + str(self.uuid)


    @override
    @property
    def schedulable_instance(self) -> Task:
        return self.task
