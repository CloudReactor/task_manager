from typing import override

from django.db import models

from ..common.utils import strip_prefix_before_last_dot
from .schedulable_instance_event import SchedulableInstanceEvent
from .workflow import Workflow

class WorkflowEvent(SchedulableInstanceEvent):
    workflow = models.ForeignKey(Workflow, null=True, blank=True, on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.workflow and not self.created_by_group:
            self.created_by_group = self.workflow.created_by_group


    def __str__(self) -> str:
        workflow_id = str(self.workflow.uuid) if self.workflow else '[REMOVED]'
        return strip_prefix_before_last_dot(self.type) + ' Workflow ' + workflow_id \
                + ' / ' + str(self.uuid)

    @override
    @property
    def schedulable_instance(self) -> Workflow:
        return self.workflow
