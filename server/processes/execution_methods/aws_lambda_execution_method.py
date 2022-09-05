from typing import Any, FrozenSet, Optional, TYPE_CHECKING

import json
import logging

from django.utils import timezone

from rest_framework.exceptions import APIException

from pydantic import BaseModel

from botocore.exceptions import ClientError

from ..common.aws import *
from ..common.utils import deepmerge_with_lists_pair
from .aws_settings import INFRASTRUCTURE_TYPE_AWS, AwsSettings
from .aws_base_execution_method import AwsBaseExecutionMethod

if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )

from .execution_method import ExecutionMethod

logger = logging.getLogger(__name__)


class AwsLambdaExecutionMethodCapabilitySettings(BaseModel):
    runtime_id: Optional[str] = None
    function_arn: Optional[str] = None
    function_name: Optional[str] = None
    function_version: Optional[str] = None
    init_type: Optional[str] = None
    dotnet_prejit: Optional[str] = None
    function_memory_mb: Optional[int] = None
    infrastructure_website_url: Optional[str] = None

    def update_derived_attrs(self) -> None:
        logger.info("AWS Lambda Execution Method: update_derived_attrs()")

        # function_arn format:
        # arn:aws:lambda:<region>:<aws account id>:function:<function name>
        if self.function_arn is not None:
            tokens = self.function_arn.split(':')

            if (len(tokens) < 7) or (tokens[0] != 'arn') or \
                (tokens[1] != 'aws') or (tokens[2] != 'lambda') or \
                (tokens[5] != 'function'):
                logger.warning(f"AWS Lambda Execution Method: function_arn is not the expected format")
                return

            region = tokens[3]
            function_name_in_arn = tokens[6]

            self.infrastructure_website_url = \
                f"https://{region}.console.aws.amazon.com/lambda/home?" + \
                make_region_parameter(region) + "#/functions/" + \
                function_name_in_arn

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


class AwsLambdaExecutionMethodSettings(AwsLambdaExecutionMethodCapabilitySettings):
    time_zone_name: Optional[str] = None
    aws_request_id: Optional[str] = None
    cognito_identity: Optional[AwsCognitoIdentity] = None
    client_context: Optional[AwsClientContext] = None

    @staticmethod
    def from_capability(
        capability: AwsLambdaExecutionMethodCapabilitySettings) \
        -> 'AwsLambdaExecutionMethodSettings':
        settings = AwsLambdaExecutionMethodSettings()
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

    def __init__(self, task: 'Task', task_execution: Optional['TaskExecution']):
        super().__init__(self.NAME, task=task, task_execution=task_execution)

        emd, infra = ExecutionMethod.merge_execution_method_and_infrastructure_details(
            task=task, task_execution=task_execution
        )

        if task_execution:
            if emd:
                self.settings = AwsLambdaExecutionMethodSettings.parse_obj(emd)
            else:
                self.settings = AwsLambdaExecutionMethodSettings()
        else:
            if emd:
                self.settings = AwsLambdaExecutionMethodCapabilitySettings.parse_obj(emd)
            else:
                self.settings = AwsLambdaExecutionMethodCapabilitySettings()

        if (task.infrastructure_type == INFRASTRUCTURE_TYPE_AWS) or \
            (task_execution and \
            (task_execution.infrastructure_type == INFRASTRUCTURE_TYPE_AWS)):
            self.aws_settings = AwsSettings.parse_obj(infra)


    def capabilities(self) -> FrozenSet[ExecutionMethod.ExecutionCapability]:
        task = self.task

        if task.passive:
            return frozenset()

        if not (self.settings.function_name or self.settings.function_arn):
            return frozenset()

        #run_env = task.run_environment

        # TODO: handle scheduling
        return frozenset([self.ExecutionCapability.MANUAL_START])

    def manually_start(self) -> None:
        task_execution = self.task_execution

        if task_execution is None:
            raise APIException("No Task Execution found")

        task = self.task or task_execution.task
        run_env = task.run_environment

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

        success = False
        try:
            lambda_client = run_env.make_boto3_client('lambda')

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
        except Exception:
            logger.warning(f'Failed to start Task {task.uuid}', exc_info=True)

        if not success:
            from ..models import TaskExecution
            task_execution.status = TaskExecution.Status.FAILED
            task_execution.stop_reason = TaskExecution.StopReason.FAILED_TO_START
            task_execution.finished_at = timezone.now()

        task_execution.execution_method_details = deepmerge_with_lists_pair(
            (task_execution.execution_method_details or {}).copy(),
            self.settings.dict())

        task_execution.save()
