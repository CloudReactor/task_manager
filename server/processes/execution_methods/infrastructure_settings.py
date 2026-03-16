from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from .execution_method import ExecutionMethod


class InfrastructureSettings(BaseModel):
    def can_manage_infrastructure(self) -> bool:
        return False

    def can_schedule_workflow(self) -> bool:
        return False

    def update_derived_attrs(self, execution_method: ExecutionMethod | None=None) -> None:
        pass
