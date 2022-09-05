from rest_framework.exceptions import APIException

from ..common.utils import deepmerge_with_lists_pair
from .execution_method import ExecutionMethod

class AwsBaseExecutionMethod(ExecutionMethod):
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
