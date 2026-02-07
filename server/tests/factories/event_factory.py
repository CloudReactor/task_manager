from processes.models import BasicEvent, Event

import factory

from .owned_model_factory import OwnedModelFactory
from .run_environment_factory import RunEnvironmentFactory


class EventFactory(OwnedModelFactory):
    class Meta:
        model = Event

    run_environment = factory.SubFactory(RunEnvironmentFactory,
        created_by_user=factory.SelfAttribute("..created_by_user"),
        created_by_group=factory.SelfAttribute("..created_by_group"))

    severity = Event.Severity.ERROR
    error_summary = 'Error'
