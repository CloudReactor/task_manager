from __future__ import annotations

from typing import Any, TYPE_CHECKING, override

import logging
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, SerializationInfo, SerializerFunctionWrapHandler, model_serializer
from pydantic.alias_generators import to_camel


from ..common.aws import normalize_role_arn, make_aws_console_role_url
from ..common.utils import deepmerge
from .execution_method import ExecutionMethod
from .aws_settings import INFRASTRUCTURE_TYPE_AWS, AwsSettings


if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )


logger = logging.getLogger(__name__)

# Has model_config suitable for use in boto3
class Boto3SerializableSettings(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
        from_attributes=True,
        serialize_by_alias=False,
    )

    def get_boto3_excluded_field_names(self) -> set[str]:
        """Override in subclasses to exclude specific fields from to_boto3_dict()"""
        return set()

    def get_all_boto3_excluded_fields(self) -> set[str]:
        """Return a set of field names to exclude from to_boto3_dict()"""
        excluded = self.get_boto3_excluded_field_names()
        
        # Automatically exclude fields ending with _infrastructure_website_url
        for field_name in self.model_fields:
            if field_name.endswith('_infrastructure_website_url') or (field_name == 'infrastructure_website_url'):
                excluded.add(field_name)
        
        return excluded

    @model_serializer(mode='wrap')
    def _boto3_serializer(self, handler: SerializerFunctionWrapHandler, info: SerializationInfo) -> dict[str, Any]:
        result = handler(self)
        if info.by_alias:
            for field_name in self.get_all_boto3_excluded_fields():
                result.pop(to_camel(field_name), None)
        return result

    def to_boto3_dict(self) -> dict[str, Any]:
        return self.model_dump(mode='json', by_alias=True, exclude_unset=True, exclude_none=True)
    
    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        pass
class AwsSubSettingsWithRole(Boto3SerializableSettings):
    role_arn: str | None = None
    role_infrastructure_website_url: str | None = None

    @override
    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        if aws_settings:
            aws_account_id = aws_settings.account_id
            region = aws_settings.region

            if aws_account_id and region and self.role_arn:
                self.role_arn = normalize_role_arn(self.role_arn,
                        aws_account_id=aws_account_id)

        self.role_infrastructure_website_url = make_aws_console_role_url(self.role_arn)

class AwsBaseExecutionMethod(ExecutionMethod):
    def __init__(self, name: str,
            task: Task | None = None,
            task_execution: TaskExecution | None = None,
            aws_settings: dict[str, Any] | None = None) -> None:
        super().__init__(name, task=task, task_execution=task_execution)

        if aws_settings is None:
            self.aws_settings = self.merge_aws_settings(task=task,
                task_execution=task_execution)
        else:
            self.aws_settings = AwsSettings.model_validate(aws_settings)


    @staticmethod
    def merge_aws_settings(task: Task | None,
            task_execution: TaskExecution | None) -> AwsSettings:
        settings_to_merge: list[dict[str, Any]] = [ {} ]

        if task:
            if task.run_environment and task.run_environment.aws_settings:
                settings_to_merge.append(task.run_environment.aws_settings)

            if task.infrastructure_settings and \
                    (task.infrastructure_type == INFRASTRUCTURE_TYPE_AWS):
                settings_to_merge.append(task.infrastructure_settings)

        if task_execution and task_execution.infrastructure_settings and \
                (task_execution.infrastructure_type == INFRASTRUCTURE_TYPE_AWS):
            settings_to_merge.append(task_execution.infrastructure_settings)

        return AwsSettings.model_validate(deepmerge(*settings_to_merge))

    def compute_region(self) -> str | None:
        region = self.aws_settings.region

        if (not region) and self.task:
            infra = self.task.infrastructure_settings
            if infra and (self.task.infrastructure_type == INFRASTRUCTURE_TYPE_AWS):
                region = infra.get('region')

                if (not region) and infra.get('network'):
                    region = infra['network'].get('region')

            if not region:
                run_environment = self.task.run_environment
                if run_environment:
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
            aws_settings = AwsSettings.model_validate(aws_settings_dict)

            aws_settings.update_derived_attrs(execution_method=self)

            self.task.infrastructure_settings = deepmerge(
                    aws_settings_dict, aws_settings.model_dump())

        # TODO: scheduling URLs

    def enrich_task_execution_settings(self) -> None:
        if not self.task_execution:
            raise RuntimeError("enrich_task_execution_settings(): No Task Execution found")

        aws_settings_dict = self.task_execution.infrastructure_settings

        if aws_settings_dict:
            aws_settings = AwsSettings.model_validate(aws_settings_dict)

            aws_settings.update_derived_attrs(execution_method=self)

            self.task_execution.infrastructure_settings = deepmerge(
                    aws_settings_dict, aws_settings.model_dump())

    @override
    def logs_url(self) -> str | None:
        if not self.task:
            return None

        lq = self.task.log_query

        if not lq:
            return None

        region = self.compute_region()

        if not region:
            logger.warning("Could not determine AWS region for logs URL")
            return None
        
        limit = 2000
        
        return f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logs-insights:queryDetail=~(end~0~start~-86400~timeType~'RELATIVE~unit~'seconds~editorString~'fields*20*40timestamp*2c*20*40message*0a*7c*20sort*20*40timestamp*20desc*0a*7c*20limit*20{limit}~isLiveTail~false~source~(~'" + \
                quote(lq, safe='').replace('%', '*') + '))'
