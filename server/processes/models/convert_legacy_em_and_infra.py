import logging

from typing import Any

from ..execution_methods import (
    AwsSettings,
    AwsEcsExecutionMethodSettings
)
from .run_environment import RunEnvironment
from .task import Task


logger = logging.getLogger(__name__)


def convert_empty_to_none_values(d: dict[str, Any]) -> dict[str, Any]:
    return { k: (None if v == '' else v) for (k, v) in d.items() }


def compute_region(
    task: Task
) -> str | None:
    region = task.run_environment.aws_default_region
    cluster_arn = task.aws_ecs_default_cluster_arn
    if not cluster_arn:
        return region

    if cluster_arn.startswith("arn:aws:ecs:"):
        parts = cluster_arn.split(":")
        return parts[3]

    logger.warning(f"Can't determine AWS region from cluster ARN '{cluster_arn}'")
    return region


def extract_infra_from_run_environment(run_environment: RunEnvironment) -> dict[str, Any]:
    aws = convert_empty_to_none_values({
        'account_id': run_environment.aws_account_id,
        'region': run_environment.aws_default_region,
        'access_key': run_environment.aws_access_key,
        'secret_key': run_environment.aws_secret_key,
        'events_role_arn': run_environment.aws_events_role_arn,
        'assumed_role_external_id': run_environment.aws_assumed_role_external_id,
        'execution_role_arn': run_environment.aws_ecs_default_execution_role,
        'workflow_starter_lambda_arn': run_environment.aws_workflow_starter_lambda_arn,
        'workflow_starter_access_key': run_environment.aws_workflow_starter_access_key,
        'network': convert_empty_to_none_values({
            'region': run_environment.aws_default_region,
            'subnets': run_environment.aws_default_subnets,
            'security_groups': run_environment.aws_ecs_default_security_groups,
            'assign_public_ip': run_environment.aws_ecs_default_assign_public_ip
        })
    })

    if run_environment.aws_tags is not None:
        aws['tags'] = run_environment.aws_tags

    logger.info(f"{aws=}")

    return aws


def populate_run_environment_infra(run_environment: RunEnvironment) -> bool:
    if run_environment.aws_account_id or run_environment.aws_events_role_arn:
        run_environment.aws_settings = extract_infra_from_run_environment(
                run_environment)

        if run_environment.aws_settings:
            aws_settings = AwsSettings.model_validate(run_environment.aws_settings)
            aws_settings.update_derived_attrs()
            run_environment.aws_settings = aws_settings.model_dump()

        return True
    else:
        return False


def extract_aws_ecs_configuration(run_environment: RunEnvironment) -> dict[str, Any]:
    return convert_empty_to_none_values({
        'launch_type': run_environment.aws_ecs_default_launch_type,
        'supported_launch_types': run_environment.aws_ecs_supported_launch_types,
        'cluster_arn': run_environment.aws_ecs_default_cluster_arn,
        'execution_role_arn': run_environment.aws_ecs_default_execution_role,
        'task_role_arn': run_environment.aws_ecs_default_task_role,
        'platform_version': run_environment.aws_ecs_default_platform_version,
    })


def populate_run_environment_aws_ecs_configuration(run_environment: RunEnvironment) -> bool:
    if run_environment.aws_ecs_default_cluster_arn or run_environment.aws_ecs_default_execution_role:
        aws_ecs_config = extract_aws_ecs_configuration(run_environment)

        if aws_ecs_config:
            aws_ecs_settings = AwsEcsExecutionMethodSettings.model_validate(
                    aws_ecs_config)
            aws_ecs_settings.update_derived_attrs(aws_settings=None)
            aws_ecs_config = aws_ecs_settings.model_dump()

        run_environment.default_aws_ecs_configuration = aws_ecs_config

        return True
    else:
        return False
