from typing import Any, FrozenSet, Optional, TYPE_CHECKING, cast, override

import json
import logging

from django.utils import timezone

from rest_framework.exceptions import APIException

from pydantic import BaseModel

from botocore.exceptions import ClientError

from ..common.aws import *
from ..common.utils import deepmerge
from .execution_method import ExecutionMethod
from .aws_base_execution_method import AwsBaseExecutionMethod
from .aws_settings import *

if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )


logger = logging.getLogger(__name__)


class AwsLambdaExecutionMethodSettings(BaseModel):
    runtime_id: Optional[str] = None
    function_arn: Optional[str] = None
    function_name: Optional[str] = None
    function_version: Optional[str] = None
    init_type: Optional[str] = None
    dotnet_prejit: Optional[str] = None
    function_memory_mb: Optional[int] = None
    infrastructure_website_url: Optional[str] = None

    def update_derived_attrs(self, aws_settings: Optional[AwsSettings] = None,
            execution_method: Optional[ExecutionMethod] = None) -> None:
        logger.info("AWS Lambda Execution Method: update_derived_attrs()")

        self.infrastructure_website_url = make_aws_console_lambda_function_url(
                function_arn=self.function_arn)

        logger.debug(f"{self.infrastructure_website_url=}")


class AwsCognitoIdentity(BaseModel):
    id: Optional[str] = None
    pool_id: Optional[str] = None


class AwsCognitoClient(BaseModel):
    installation_id: Optional[str] = None
    app_title: Optional[str] = None
    app_version_name: Optional[str] = None
    app_version_code: Optional[str] = None
    app_package_name: Optional[str] = None


class AwsClientContext(BaseModel):
    client: Optional[AwsCognitoClient] = None
    custom: Optional[dict[str, Any]] = None
    env: Optional[dict[str, Any]] = None


class AwsLambdaExecutionMethodInfo(AwsLambdaExecutionMethodSettings):
    time_zone_name: Optional[str] = None
    aws_request_id: Optional[str] = None
    cognito_identity: Optional[AwsCognitoIdentity] = None
    client_context: Optional[AwsClientContext] = None

    @staticmethod
    def from_capability(
        capability: AwsLambdaExecutionMethodSettings) \
        -> 'AwsLambdaExecutionMethodInfo':
        settings = AwsLambdaExecutionMethodInfo()
        settings.runtime_id = capability.runtime_id
        settings.function_arn = capability.function_arn
        settings.function_name = capability.function_name
        settings.function_version = capability.function_version
        settings.init_type = capability.init_type
        settings.dotnet_prejit = capability.dotnet_prejit
        settings.function_memory_mb = capability.function_memory_mb
        settings.infrastructure_website_url = capability.infrastructure_website_url
        return settings


class AwsLambdaExecutionMethod(AwsBaseExecutionMethod):
    NAME = "AWS Lambda"

    def __init__(self, task: Optional['Task'],
            task_execution: Optional['TaskExecution'],
            aws_settings: Optional[dict[str, Any]] = None,
            aws_lambda_settings: Optional[dict[str, Any]] = None):
        super().__init__(self.NAME, task=task, task_execution=task_execution,
                aws_settings=aws_settings)

        task = self.task

        if aws_lambda_settings is None:
            settings_to_merge: list[dict[str, Any]] = [ {} ]

            if task:
                settings_to_merge = []

                if task.run_environment:
                    settings_to_merge.append(task.run_environment.default_aws_lambda_configuration or {})

                settings_to_merge.append(task.execution_method_capability_details or {})

            if task_execution and task_execution.execution_method_details:
                settings_to_merge.append(task_execution.execution_method_details)

            aws_lambda_settings = deepmerge(*settings_to_merge)

        logger.debug(f"{aws_lambda_settings=}")

        if task_execution:
            self.settings = cast(AwsLambdaExecutionMethodSettings,
                    AwsLambdaExecutionMethodInfo.parse_obj(aws_lambda_settings))
        else:
            self.settings = AwsLambdaExecutionMethodSettings.parse_obj(
                    aws_lambda_settings)


    @override
    def capabilities(self) -> FrozenSet[ExecutionMethod.ExecutionCapability]:
        task = self.task

        if task and task.passive:
            return frozenset()

        if not (self.settings.function_name or self.settings.function_arn):
            return frozenset()

        network = self.aws_settings.network

        subnets: Optional[list[str]] = None
        security_groups: Optional[list[str]] = None

        if network:
            subnets = network.subnets
            security_groups = network.security_groups

        if (not subnets) or (not security_groups) :
            return frozenset()

        # TODO: handle scheduling
        return frozenset([self.ExecutionCapability.MANUAL_START])

    @override
    def manually_start(self) -> None:
        task_execution = self.task_execution

        if task_execution is None:
            raise APIException("No Task Execution found")

        task = self.task

        if task is None:
            raise APIException("No Task found")

        function_name = self.settings.function_arn or self.settings.function_name

        # Allow more params to be set, as well as the environment if the
        # input can be trusted.
        payload = {
            'original_input_value': task_execution.input_value,
            'cloudreactor_context': {
                'proc_wrapper_params': {
                    'task_execution': {
                        'uuid': str(task_execution.uuid)
                    }
                }
            }
        }

        task_execution.execution_method_type = self.NAME
        task_execution.execution_method_details = self.settings.dict()

        success = False
        try:
            lambda_client = self.aws_settings.make_boto3_client('lambda',
                session_uuid=str(task_execution.uuid))

            # TODO: environment override?
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='Event',
                LogType='None',
                # Client context is dropped in async invocations
                # https://github.com/aws/aws-sdk-js/issues/1388#issuecomment-403466618
                # ClientContext='',
                Payload=json.dumps(payload).encode('utf-8'))

            logger.info(f"Got invoke() return value {response}")

            self.settings.function_version = response.get('ExecutedVersion')

            success = True
        except ClientError as client_error:
            logger.warning(f'Failed to start Task {task.uuid}', exc_info=True)
            task_execution.error_details = client_error.response
        except Exception as ex:
            logger.warning(f'Failed to start Task {task.uuid}', exc_info=True)
            task_execution.error_details = {
                'exception': str(ex)
            }

        if not success:
            from ..models import TaskExecution
            task_execution.status = Execution.Status.FAILED
            task_execution.stop_reason = TaskExecution.StopReason.FAILED_TO_START
            task_execution.finished_at = timezone.now()

        task_execution.execution_method_details = self.settings.dict()
        task_execution.save()

    @override
    def enrich_task_settings(self) -> None:
        logger.info("AwsLambdaExecutionMethod: enrich_task_settings()")

        if not self.task:
            raise RuntimeError("No Task found")

        super().enrich_task_settings()

        emcd = self.task.execution_method_capability_details
        if emcd:
            aws_lambda_settings = AwsLambdaExecutionMethodSettings.parse_obj(emcd)
            aws_lambda_settings.update_derived_attrs(aws_settings=self.aws_settings,
                execution_method=self)
            self.task.execution_method_capability_details = aws_lambda_settings.dict()


    @override
    def enrich_task_execution_settings(self) -> None:
        if self.task_execution is None:
            raise APIException("enrich_task_settings(): Missing Task Execution")

        super().enrich_task_execution_settings()

        emd = self.task_execution.execution_method_details

        if emd:
            aws_lambda_settings =  AwsLambdaExecutionMethodInfo.parse_obj(emd)
            aws_lambda_settings.update_derived_attrs(aws_settings=self.aws_settings)

            self.task_execution.execution_method_details = deepmerge(
                    emd, aws_lambda_settings.dict())
