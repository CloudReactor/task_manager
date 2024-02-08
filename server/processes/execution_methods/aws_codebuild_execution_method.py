from typing import Any, FrozenSet, Optional, TYPE_CHECKING, cast
from collections import abc

import logging

from django.utils import timezone

from rest_framework.exceptions import APIException

from pydantic import BaseModel

from botocore.exceptions import ClientError

from ..common.aws import *
from ..common.utils import deepmerge, lookup_string, lookup_int, lookup_bool, to_camel
from .execution_method import ExecutionMethod
from .aws_base_execution_method import AwsBaseExecutionMethod
from .aws_settings import *

if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )


logger = logging.getLogger(__name__)


class AwsCodeBuildCache(BaseModel):
    type: Optional[str] = None
    location: Optional[str] = None
    modes: Optional[list[str]] = None


class AwsCodeBuildArtifact(BaseModel):
    location: Optional[str] = None
    sha256_sum: Optional[str] = None
    md5_sum: Optional[str] = None
    override_artifact_name: Optional[str] = None
    encryption_disabled: Optional[bool] = None
    artifact_identifier: Optional[str] = None
    bucket_owner_access: Optional[str] = None

    class Config:
        alias_generator = to_camel

        # Change to populate_by_name for pydantic V2
        allow_population_by_field_name = True


class AwsCodeBuildExecutionMethodSettings(BaseModel):
    build_arn: Optional[str] = None
    build_image: Optional[str] = None
    initiator: Optional[str] = None
    source_repo_url: Optional[str] = None
    source_version: Optional[str] = None
    source_version_infrastructure_website_url: Optional[str] = None
    environment_type: Optional[str] = None
    compute_type: Optional[str] = None
    privileged_mode: Optional[bool] = None
    image_pull_credentials_type: Optional[str] = None
    kms_key_id: Optional[str] = None
    kms_key_infrastructure_website_url: Optional[str] = None
    service_role: Optional[str] = None
    service_role_infrastructure_website_url: Optional[str] = None
    timeout_in_minutes: Optional[int] = None
    queued_timeout_in_minutes: Optional[int] = None
    cache: Optional[AwsCodeBuildCache] = None
    artifacts: Optional[AwsCodeBuildArtifact] = None
    secondary_artifacts: Optional[list[AwsCodeBuildArtifact]] = None
    debug_session_enabled: Optional[bool] = None
    assumed_role_arn: Optional[str] = None
    assumed_role_infrastructure_website_url: Optional[str] = None

    infrastructure_website_url: Optional[str] = None
    project_name: Optional[str] = None


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        try:
            self.update_derived_attrs()
        except Exception as ex: # pylint: disable=broad-except
            logger.warning(f"Failed to update derived attributes: {ex}")  # pragma: no cover

    def update_derived_attrs(self, aws_settings: Optional[AwsSettings]=None) -> None:
        logger.info("AWS CodeBuild Execution Method: update_derived_attrs()")

        if self.build_arn:
            tokens = self.build_arn.split(':')

            if (not self.project_name) and (len(tokens) >= 6) and tokens[5].startswith('build/'):
                self.project_name = tokens[5][len('build/'):]

            self.infrastructure_website_url = make_aws_console_codebuild_build_url(
                    build_arn=self.build_arn)

            logger.debug(f"{self.infrastructure_website_url=}")

        if self.source_version and self.source_version.startswith('arn:aws:s3:::'):
            self.source_version_infrastructure_website_url = make_aws_console_s3_object_url(
                    self.source_version)

        if self.service_role:
            self.service_role_infrastructure_website_url = make_aws_console_role_url(
                    role_arn=self.service_role)

        if self.kms_key_id and aws_settings and aws_settings.region:
            self.kms_key_infrastructure_website_url = make_aws_console_kms_key_url(
                    key_id=self.kms_key_id, region=aws_settings.region)

        if self.assumed_role_arn:
            self.assumed_role_infrastructure_website_url = make_aws_console_role_url(
                    role_arn=self.assumed_role_arn)


    def compute_region(self) -> Optional[str]:
        if self.build_arn:
            tokens = self.build_arn.split(':')
            if len(tokens) >= 6:
                return tokens[3]

        return None

    def update_from_start_build_response(self, response: dict[str, Any]) -> None:
        build_dict = response.get('build')

        if not isinstance(build_dict, abc.Mapping):
            logger.warning(f"AwsCodeBuildExecutionMethodSettings.update_from_start_build_response(): Can't find 'build' property in start_build() {response=}")
            return

        self.build_arn = lookup_string(build_dict, 'arn')
        self.kms_key_id = lookup_string(build_dict, 'encryptionKey')
        self.service_role = lookup_string(build_dict, 'serviceRole')
        self.timeout_in_minutes = lookup_int(build_dict, 'timeoutInMinutes')
        self.queued_timeout_in_minutes = lookup_int(build_dict, 'queuedTimeoutInMinutes')
        self.initiator = lookup_string(build_dict, 'initiator')

        environment = build_dict.get('environment')

        if isinstance(environment, abc.Mapping):
            self.environment_type = lookup_string(environment, 'type')
            self.build_image = lookup_string(environment, 'image')
            self.compute_type = lookup_string(environment, 'computeType')
            self.privileged_mode = lookup_string(environment, 'privilegedMode')
            self.image_pull_credentials_type = lookup_string(environment, 'imagePullCredentialsType')

        artifact_dict = build_dict.get('artifacts')
        if artifact_dict:
            self.artifacts = AwsCodeBuildArtifact.parse_obj(artifact_dict)

        secondary_artifacts_dicts = build_dict.get('secondaryArtifacts')
        if secondary_artifacts_dicts:
            self.secondary_artifacts = [AwsCodeBuildArtifact.parse_obj(sad) for sad in secondary_artifacts_dicts]

        cache_dict = build_dict.get('cache')
        if cache_dict:
            self.cache = AwsCodeBuildCache.parse_obj(cache_dict)


class AwsCodeBuildWebhookInfo(BaseModel):
    actor_account_id: Optional[str] = None
    base_ref: Optional[str] = None
    event: Optional[str] = None
    merge_commit: Optional[str] = None
    prev_commit: Optional[str] = None
    head_ref: Optional[str] = None
    trigger: Optional[str] = None


class AwsCodeBuildReport(BaseModel):
    report_arn: Optional[str] = None

    class Config:
        alias_generator = to_camel

        # Change to populate_by_name for pydantic V2
        allow_population_by_field_name = True


class AwsCodeBuildProjectFileSystemLocation(BaseModel):
    type: Optional[str] = None
    location: Optional[str] = None
    mount_point: Optional[str] = None
    identifier: Optional[str] = None
    mount_options: Optional[str] = None

    class Config:
        alias_generator = to_camel

        # Change to populate_by_name for pydantic V2
        allow_population_by_field_name = True


class AwsCodeBuildDebugSession(BaseModel):
    session_enabled: Optional[bool] = None
    session_target: Optional[str] = None

    class Config:
        alias_generator = to_camel

        # Change to populate_by_name for pydantic V2
        allow_population_by_field_name = True


class AwsCodeBuildExecutionMethodInfo(AwsCodeBuildExecutionMethodSettings):
    build_id: Optional[str] = None
    build_number: Optional[int] = None
    batch_build_identifier: Optional[str] = None
    build_batch_arn: Optional[str] = None
    resolved_source_version: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    current_phase: Optional[str] = None
    build_status: Optional[str] = None
    build_succeeding: Optional[bool] = None # From proc_wrapper
    build_complete: Optional[bool] = None
    public_build_url: Optional[str] = None
    webhook: Optional[AwsCodeBuildWebhookInfo] = None # From proc_wrapper
    file_system_locations: Optional[list[AwsCodeBuildProjectFileSystemLocation]] = None
    cache: Optional[AwsCodeBuildCache] = None
    reports: Optional[list[AwsCodeBuildReport]] = None
    debug_session: Optional[AwsCodeBuildDebugSession] = None

    def update_from_start_build_response(self, response: dict[str, Any]) -> None:
        super().update_from_start_build_response(response=response)

        build_dict = response.get('build')

        if not isinstance(build_dict, abc.Mapping):
            logger.warning(f"AwsCodeBuildExecutionMethodInfo.update_from_start_build_response(): Can't find 'build' property in start_build() {response=}")
            return

        self.build_id = build_dict.get('id')
        self.build_number = lookup_int(build_dict, 'buildNumber')
        self.build_batch_arn = lookup_string(build_dict, 'buildBatchArn')
        self.source_version = lookup_string(build_dict, 'sourceVersion')
        self.resolved_source_version = lookup_string(build_dict, 'resolvedSourceVersion')
        self.start_time = lookup_string(build_dict, 'startTime')
        self.end_time = lookup_string(build_dict, 'endTime')
        self.current_phase = lookup_string(build_dict, 'currentPhase')
        self.build_status = lookup_string(build_dict, 'buildStatus')
        self.build_complete = lookup_bool(build_dict, 'buildComplete')

        report_arns = build_dict.get('reportArns')
        if report_arns:
            self.reports = [AwsCodeBuildReport(report_arn=arn) for arn in report_arns]

        debug_session_dict = build_dict.get('debugSession')
        if debug_session_dict:
            self.debug_session = AwsCodeBuildDebugSession.parse_obj(debug_session_dict)


class AwsCodeBuildExecutionMethod(AwsBaseExecutionMethod):
    NAME = "AWS CodeBuild"

    def __init__(self, task: Optional['Task'],
            task_execution: Optional['TaskExecution'],
            aws_settings: Optional[dict[str, Any]] = None,
            aws_codebuild_settings: Optional[dict[str, Any]] = None):
        super().__init__(self.NAME, task=task, task_execution=task_execution,
                aws_settings=aws_settings)

        task = self.task

        if aws_codebuild_settings is None:
            settings_to_merge: list[dict[str, Any]] = [ {} ]

            if task:
                settings_to_merge = [
                    task.execution_method_capability_details or {}
                ]

            if task_execution and task_execution.execution_method_details:
                settings_to_merge.append(task_execution.execution_method_details)

            aws_codebuild_settings = deepmerge(*settings_to_merge)

        logger.debug(f"{aws_codebuild_settings=}")

        if task_execution:
            self.settings = cast(AwsCodeBuildExecutionMethodSettings,
                    AwsCodeBuildExecutionMethodInfo.parse_obj(aws_codebuild_settings))
        else:
            self.settings = AwsCodeBuildExecutionMethodSettings.parse_obj(
                    aws_codebuild_settings)

    def capabilities(self) -> FrozenSet[ExecutionMethod.ExecutionCapability]:
        task = self.task

        if task and task.passive:
            return frozenset()

        if not self.settings.project_name:
            return frozenset()

        # TODO: handle scheduling
        return frozenset([self.ExecutionCapability.MANUAL_START])


    def manually_start(self) -> None:
        task_execution = self.task_execution

        if task_execution is None:
            raise APIException("No Task Execution found")

        task = self.task

        if task is None:
            raise APIException("No Task found")

        project_name = self.settings.project_name

        if not project_name:
            raise APIException("No project name found")

        task_env = task_execution.make_environment()

        task_env["CLOUDREACTOR_RUN_ENVIRONMENT_NAME"] = task.run_environment.name

        # For scripts that assume role before passing temp credentials to Docker,
        # such as cr_deploy.sh in the AWS ECS Deployer.
        if self.settings.assumed_role_arn:
            task_env['CLOUDREACTOR_DEPLOYER_ASSUME_ROLE_ARN'] = self.settings.assumed_role_arn

        flattened_env = make_flattened_environment(env=task_env)

        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/codebuild/client/start_build.html
        start_build_args: dict[str, Any] = {
            'projectName': project_name,
            'environmentVariablesOverride': flattened_env
        }

        # CHECKME: depends on source type
        if self.settings.source_version:
            start_build_args['sourceVersion'] = self.settings.source_version

        if self.settings.build_image:
            start_build_args['imageOverride'] = self.settings.build_image

        if self.settings.artifacts:
            start_build_args['artifactsOverride'] = self.settings.artifacts.dict(by_alias=True)
        else:
            artifacts_type = 'NO_ARTIFACTS'

            if self.settings.initiator and self.settings.initiator.startswith('codepipeline/'):
                artifacts_type = 'CODEPIPELINE'

            start_build_args['artifactsOverride'] = {
                'type': artifacts_type
            }

        if self.settings.secondary_artifacts:
            start_build_args['secondaryArtifactsOverride'] = [sad.dict(by_alias=True) for sad in self.settings.secondary_artifacts]

        if self.settings.cache:
            start_build_args['cacheOverride'] = self.settings.cache.dict(by_alias=True)

        if self.settings.service_role:
            start_build_args['serviceRoleOverride'] = self.settings.service_role

        if self.settings.timeout_in_minutes is not None:
            start_build_args['timeoutInMinutesOverride'] = self.settings.timeout_in_minutes

        if self.settings.queued_timeout_in_minutes is not None:
            start_build_args['queuedTimeoutInMinutesOverride'] = self.settings.queued_timeout_in_minutes

        if self.settings.kms_key_id:
            start_build_args['encryptionKeyOverride'] = self.settings.kms_key_id

        log_settings = self.aws_settings.logging
        if log_settings and (log_settings.driver == 'awslogs'):
            log_options = log_settings.options
            if log_options and log_options.group:
                cloudwatch_logs_options = {
                    'status': 'ENABLED',
                    'groupName': log_options.group
                }

                stream_name = log_options.stream
                if stream_name:
                    cloudwatch_logs_options['streamName'] = stream_name

                start_build_args['logsConfigOverride'] = {
                    'cloudwatchLogs': cloudwatch_logs_options
                }

        # TODO: registryCredentialOverride

        if self.settings.image_pull_credentials_type:
            start_build_args['imagePullCredentialsTypeOverride'] = self.settings.image_pull_credentials_type

        if self.settings.debug_session_enabled:
            start_build_args['debugSessionEnabled'] = self.settings.debug_session_enabled

        task_execution.execution_method_type = self.NAME
        task_execution.execution_method_details = self.settings.dict()

        success = False
        try:
            codebuild_client = self.aws_settings.make_boto3_client('codebuild',
                session_uuid=str(task_execution.uuid))

            response = codebuild_client.start_build(**start_build_args)

            logger.info(f"Got start_build() return value {response}")

            self.settings.update_from_start_build_response(response)

            self.update_aws_settings_from_start_build_response(response)

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
            task_execution.status = TaskExecution.Status.FAILED
            task_execution.stop_reason = TaskExecution.StopReason.FAILED_TO_START
            task_execution.finished_at = timezone.now()

        task_execution.execution_method_details = self.settings.dict()
        task_execution.infrastructure_settings = self.aws_settings.dict()
        task_execution.save()

    def enrich_task_settings(self) -> None:
        if not self.task:
            raise RuntimeError("No Task found")

        super().enrich_task_settings()

        emcd = self.task.execution_method_capability_details
        if emcd:
            aws_codebuild_settings = AwsCodeBuildExecutionMethodSettings.parse_obj(emcd)
            aws_codebuild_settings.update_derived_attrs(aws_settings=self.aws_settings)
            self.task.execution_method_capability_details = aws_codebuild_settings.dict()


    def enrich_task_execution_settings(self) -> None:
        if self.task_execution is None:
            raise APIException("enrich_task_settings(): Missing Task Execution")

        super().enrich_task_execution_settings()

        emd = self.task_execution.execution_method_details

        if emd:
            aws_codebuild_settings =  AwsCodeBuildExecutionMethodInfo.parse_obj(emd)
            aws_codebuild_settings.update_derived_attrs(aws_settings=self.aws_settings)

            self.task_execution.execution_method_details = deepmerge(
                    emd, aws_codebuild_settings.dict())


    def update_aws_settings_from_start_build_response(self, response: dict[str, Any]) -> None:
        build_dict = response.get('build')

        if not isinstance(build_dict, abc.Mapping):
            logger.warning(f"Can't find 'build' property in start_build() {response=}")
            return

        region: Optional[str] = self.settings.compute_region()

        network_settings = self.aws_settings.network or AwsNetworkSettings()
        self.aws_settings.network = network_settings

        if region:
            network_settings.region = network_settings.region or region
        else:
            region = network_settings.region

        logs_dict = build_dict.get('logs')

        if logs_dict:
            logging_settings = self.aws_settings.logging or AwsLoggingSettings()
            self.aws_settings.logging = logging_settings

            cloudwatch_logs_dict = logs_dict.get('cloudwatchLogs')

            if cloudwatch_logs_dict:
                if cloudwatch_logs_dict.get('status') == 'ENABLED':
                    logging_settings.driver = 'awslogs'
                    log_options = logging_settings.options or AwsLogOptions()

                    if not logging_settings.region:
                        logging_settings.region = region

                    logging_settings.options = log_options
                    log_options.group = lookup_string(cloudwatch_logs_dict, 'groupName')
                    log_options.stream = lookup_string(cloudwatch_logs_dict, 'streamName')

            # TODO: S3 logging, deeplinks

        vpc_dict = build_dict.get('vpcConfig')

        if vpc_dict:
            network_settings.vpc_id = lookup_string(vpc_dict, 'vpcId')
            network_settings.subnets = vpc_dict.get('subnets')
            network_settings.security_groups = vpc_dict.get('securityGroupIds')

        network_interface_dict = build_dict.get('networkInterface')

        if network_interface_dict:
            network_settings.selected_subnet = lookup_string(network_interface_dict, 'subnetId')
