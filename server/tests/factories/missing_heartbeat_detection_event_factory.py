from django.utils import timezone

from processes.models import MissingHeartbeatDetectionEvent

import factory
from pytest_factoryboy import register

from .event_factory import EventFactory

from .task_factory import TaskFactory
from .task_execution_factory import TaskExecutionFactory


@register
class MissingHeartbeatDetectionEventFactory(EventFactory):
    class Meta:
        model = MissingHeartbeatDetectionEvent

    task = factory.SubFactory(TaskFactory)
    task_execution = factory.SubFactory(TaskExecutionFactory)

    severity = MissingHeartbeatDetectionEvent.Severity.ERROR
    last_heartbeat_at = factory.LazyFunction(timezone.now)
    expected_heartbeat_at = factory.LazyFunction(timezone.now)
    heartbeat_interval_seconds = 60
