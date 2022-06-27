import logging

from rest_framework import serializers

from processes.models import InsufficientServiceInstancesEvent
from . import NameAndUuidSerializer

logger = logging.getLogger(__name__)


class InsufficientServiceInstancesEventSerializer(serializers.ModelSerializer):
    """
    Represents an event that is created when the number of running
    Task Executions for a service Task goes below min_service_instance_count
    of the Task.
    """

    class Meta:
        model = InsufficientServiceInstancesEvent
        fields = ('uuid', 'task',
                  'interval_start_at', 'interval_end_at',
                  'detected_concurrency', 'required_concurrency',
                  'detected_at', 'resolved_at',)

    task = NameAndUuidSerializer(view_name='tasks-detail')
