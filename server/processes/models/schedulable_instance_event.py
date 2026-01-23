from __future__ import annotations

from typing import TYPE_CHECKING

from .event import Event

if TYPE_CHECKING:
    from .schedulable import Schedulable

class SchedulableInstanceEvent(Event):
    @property
    def schedulable_instance(self) -> Schedulable:
        raise NotImplementedError()
