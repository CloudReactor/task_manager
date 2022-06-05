
from processes.models import AlertMethod

import factory

from .owned_model_factory import OwnedModelFactory


class AlertMethodFactory(OwnedModelFactory):
    class Meta:
        model = AlertMethod

    name = factory.Sequence(lambda n: f'alert_method_{n}')

    notify_on_success = False
    notify_on_failure = True
    notify_on_timeout = True
    error_severity_on_missing_execution = 'error'
    error_severity_on_missing_heartbeat = 'error'
    error_severity_on_service_down = 'error'

    enabled = True
