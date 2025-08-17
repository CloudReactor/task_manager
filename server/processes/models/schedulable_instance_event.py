from .event import Event

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schedulable import Schedulable

class SchedulableInstanceEvent(Event):
    @property
    def schedulable_instance(self) -> 'Schedulable':
        raise NotImplementedError()
