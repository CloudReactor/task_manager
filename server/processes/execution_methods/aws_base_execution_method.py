from typing import Any, Optional, TYPE_CHECKING

import logging

from rest_framework.exceptions import APIException

from ..common.utils import deepmerge, deepmerge_with_lists_pair
from .execution_method import ExecutionMethod
from .aws_settings import AwsSettings

if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )


logger = logging.getLogger(__name__)


class AwsBaseExecutionMethod(ExecutionMethod):
    def __init__(self, name: str,
            task: Optional['Task'] = None,
            task_execution: Optional['TaskExecution'] = None,
            aws_settings: Optional[dict[str, Any]] = None) -> None:
        super().__init__(name, task=task,
                task_execution=task_execution)

        if aws_settings is None:
            settings_to_merge = [ {} ]

            if task and task.infrastructure_settings:
                settings_to_merge.append(task.infrastructure_settings)

            if task_execution and task_execution.infrastructure_settings:
                settings_to_merge.append(task_execution.infrastructure_settings)

            aws_settings = deepmerge(*settings_to_merge)

        logger.debug(f"Merged {aws_settings=}")

        self.aws_settings = AwsSettings.parse_obj(aws_settings)


    # FIXME, these overwrite task settings with settings from RunEnvironment
    def enrich_task_settings(self) -> None:
        self.settings.update_derived_attrs()
        self.task.execution_method_capability_details = deepmerge_with_lists_pair(
            self.task.execution_method_capability_details, self.settings.dict())

        if self.aws_settings:
            self.aws_settings.update_derived_attrs(
                run_environment=self.task.run_environment)
            self.task.infrastructure_settings = deepmerge_with_lists_pair(
                self.task.infrastructure_settings, self.aws_settings.dict())

        # TODO: scheduling URLs

    def enrich_task_execution_settings(self) -> None:
        if self.task_execution is None:
           raise APIException("enrich_task_settings(): Missing Task Execution")

        self.settings.update_derived_attrs()
        self.task_execution.execution_method_details = deepmerge_with_lists_pair(
            self.task_execution.execution_method_details, self.settings.dict())

        if self.aws_settings:
            self.aws_settings.update_derived_attrs(
                run_environment=self.task.run_environment)
            self.task_execution.infrastructure_settings = deepmerge_with_lists_pair(
                self.task_execution.infrastructure_settings, self.aws_settings.dict())
