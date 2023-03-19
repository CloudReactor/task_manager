from typing import Any, Optional, TYPE_CHECKING

import logging

from ..common.utils import deepmerge
from .execution_method import ExecutionMethod
from .aws_settings import INFRASTRUCTURE_TYPE_AWS, AwsSettings

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
            self.aws_settings = self.merge_aws_settings(task=task,
                task_execution=task_execution)
        else:
            self.aws_settings = AwsSettings.parse_obj(aws_settings)


    @staticmethod
    def merge_aws_settings(task: Optional['Task'],
            task_execution: Optional['TaskExecution']) -> AwsSettings:
        settings_to_merge: list[dict[str, Any]] = [ {} ]

        if task:
            if task.run_environment.aws_settings:
                settings_to_merge.append(task.run_environment.aws_settings)

            if task.infrastructure_settings and \
                    (task.infrastructure_type == INFRASTRUCTURE_TYPE_AWS):
                settings_to_merge.append(task.infrastructure_settings)

        if task_execution and task_execution.infrastructure_settings and \
                (task_execution.infrastructure_type == INFRASTRUCTURE_TYPE_AWS):
            settings_to_merge.append(task_execution.infrastructure_settings)

        return AwsSettings.parse_obj(deepmerge(*settings_to_merge))

    def compute_region(self) -> Optional[str]:
        region = self.aws_settings.region

        if (not region) and self.task:
            infra = self.task.infrastructure_settings
            if infra and (self.task.infrastructure_type == INFRASTRUCTURE_TYPE_AWS):
                region = infra.get('region')

                if (not region) and infra.get('network'):
                    region = infra['network'].get('region')

            if not region:
                run_environment = self.task.run_environment
                re_aws_settings = run_environment.aws_settings
                if re_aws_settings:
                    region = re_aws_settings.get('region')

                    if (not region) and re_aws_settings.get('network'):
                        region = re_aws_settings['network'].get('region')

        return region


    def enrich_task_settings(self) -> None:
        if not self.task:
            raise RuntimeError("enrich_task_settings(): No Task found")

        aws_settings_dict = self.task.infrastructure_settings

        if aws_settings_dict:
            aws_settings = AwsSettings.parse_obj(aws_settings_dict)

            aws_settings.update_derived_attrs(execution_method=self)

            self.task.infrastructure_settings = deepmerge(
                    aws_settings_dict, aws_settings.dict())

        # TODO: scheduling URLs

    def enrich_task_execution_settings(self) -> None:
        if not self.task_execution:
            raise RuntimeError("enrich_task_execution_settings(): No Task Execution found")

        aws_settings_dict = self.task_execution.infrastructure_settings

        if aws_settings_dict:
            aws_settings = AwsSettings.parse_obj(aws_settings_dict)

            aws_settings.update_derived_attrs(execution_method=self)

            self.task_execution.infrastructure_settings = deepmerge(
                    aws_settings_dict, aws_settings.dict())
