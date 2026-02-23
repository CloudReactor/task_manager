from typing import override

import logging

from rest_framework.exceptions import ErrorDetail

from ..exception.unprocessable_entity import UnprocessableEntity

from ..models import InsufficientServiceTaskExecutionsEvent

from .name_and_uuid_serializer import NameAndUuidSerializer
from .event_serializer import EventSerializer

logger = logging.getLogger(__name__)


class InsufficientServiceTaskExecutionsEventSerializer(EventSerializer):
    """
    Represents an event that is created when the number of running
    Task Executions for a service Task goes below min_service_instance_count
    of the Task.
    """

    task = NameAndUuidSerializer(view_name='tasks-detail')

    class Meta(EventSerializer.Meta):
        model = InsufficientServiceTaskExecutionsEvent
        fields = EventSerializer.Meta.fields + [
            'task',
            'interval_start_at',
            'interval_end_at',
            'detected_concurrency',
            'required_concurrency',
        ]

    @override
    def to_internal_value(self, data):
        """Convert nested task data to an actual instance."""
        from ..models import Task

        task_data = data.get('task', None)

        validated = super().to_internal_value(data)

        group = validated['created_by_group']
        run_environment = validated['run_environment']

        task: Task | None = None
        if task_data:
            task = Task.find_by_uuid_or_name(task_data,
                required_group=group,
                required_run_environment=run_environment)

        if task is None:
            if self.instance:
                task = self.instance.task
            else:
                raise UnprocessableEntity({
                    'task': [ErrorDetail('No Task was found for the provided identifier', code='not_found')]
                })
        elif self.instance:
            if task.pk != self.instance.task.pk:
                raise UnprocessableEntity({
                    'task': [ErrorDetail('The specified Task does not match the Task associated with the provided Event', code='mismatch')]
                })

        if run_environment and (task.run_environment.pk != run_environment.pk):
            raise UnprocessableEntity({
                'task': [ErrorDetail('The Task\'s Run Environment does not match the specified Run Environment', code='mismatch')]
            })

        validated['task'] = task

        return validated
