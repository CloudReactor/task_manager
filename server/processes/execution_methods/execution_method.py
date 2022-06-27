from typing import FrozenSet, TYPE_CHECKING

import logging
import enum

from rest_framework.exceptions import ValidationError

from ..exception import UnprocessableEntity

if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )

logger = logging.getLogger(__name__)

class ExecutionMethod:
    @enum.unique
    class ExecutionCapability(enum.IntEnum):
        MANUAL_START = 1
        SCHEDULING = 2
        SETUP_SERVICE = 3

    ALL_CAPABILITIES = frozenset([
        ExecutionCapability.MANUAL_START,
        ExecutionCapability.SCHEDULING,
        ExecutionCapability.SETUP_SERVICE
    ])

    def __init__(self, name: str, task: 'Task'):
        self.name = name
        self.task = task

    def capabilities(self) -> FrozenSet[ExecutionCapability]:
        return frozenset()

    def supports_capability(self, cap: ExecutionCapability) -> bool:
        return cap in self.capabilities()

    def setup_scheduled_execution(self) -> None:
        raise UnprocessableEntity(
                detail='Execution method does not support scheduled execution.')

    def teardown_scheduled_execution(self) -> None:
        logger.info('teardown_service(): execution method does not support scheduled execution, no-op')

    def setup_service(self, force_creation=False) -> None:
        raise UnprocessableEntity(
                detail='Execution method does not support service setup.')

    def teardown_service(self) -> None:
        logger.info('teardown_service(): execution method does not support services, no-op')

    def manually_start(self, task_execution: 'TaskExecution') -> None:
        raise ValidationError(detail='Execution method does not support manual start.')

    def enrich_task_settings(self) -> None:
        pass
