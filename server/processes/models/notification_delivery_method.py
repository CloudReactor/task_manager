from typing import Any, Optional

from typedmodels.models import TypedModel

from .event import Event
from .named_with_uuid_and_run_environment_model import NamedWithUuidAndRunEnvironmentModel

class NotificationDeliveryMethod(TypedModel, NamedWithUuidAndRunEnvironmentModel):
    def send(self, event: Event) -> Optional[dict[str, Any]]:
        pass
