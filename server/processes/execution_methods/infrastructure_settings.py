from pydantic import BaseModel

class InfrastructureSettings(BaseModel):
    def can_manage_infrastructure(self) -> bool:
        return False

    def can_schedule_workflow(self) -> bool:
        return False

    def update_derived_attrs(self) -> None:
        pass
