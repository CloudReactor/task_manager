import logging

from typing import Any, Optional

from ..common.utils import coalesce, deepmerge_with_lists
from ..execution_methods import (
    INFRASTRUCTURE_TYPE_AWS,
    SCHEDULING_TYPE_AWS_CLOUDWATCH,
    AwsSettings,
    AwsEcsExecutionMethod,
    AwsEcsExecutionMethodSettings
)
from .run_environment import RunEnvironment
from .task import Task
from .task_execution import TaskExecution
from .aws_ecs_service_load_balancer_details import AwsEcsServiceLoadBalancerDetails


logger = logging.getLogger(__name__)


def convert_empty_to_none_values(d: dict[str, Any]) -> dict[str, Any]:
    return { k: (None if v == '' else v) for (k, v) in d.items() }


def compute_region(
    task: Task
) -> Optional[str]:
    region = task.run_environment.aws_default_region
    cluster_arn = task.aws_ecs_default_cluster_arn
    if not cluster_arn:
        return region

    if cluster_arn.startswith("arn:aws:ecs:"):
        parts = cluster_arn.split(":")
        return parts[3]

    logger.warning(f"Can't determine AWS region from cluster ARN '{cluster_arn}'")
    return region


def compute_region_from_task_execution(
    task_execution: TaskExecution
) -> Optional[str]:
    cluster_arn = task_execution.aws_ecs_cluster_arn
    if not cluster_arn:
        return None

    if cluster_arn.startswith("arn:aws:ecs:"):
        parts = cluster_arn.split(":")
        return parts[3]

    logger.warning(f"Can't determine AWS region from cluster ARN '{cluster_arn}'")
    return None


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
            aws_settings = AwsSettings.parse_obj(run_environment.aws_settings)
            aws_settings.update_derived_attrs(run_environment=run_environment)
            run_environment.aws_settings = aws_settings.dict()

        return True
    else:
        return False


def extract_aws_ecs_configuration(run_environment: RunEnvironment) -> dict[str, Any]:
    return convert_empty_to_none_values({
        'launch_type': run_environment.aws_ecs_default_launch_type,
        'supported_launch_types': run_environment.aws_ecs_supported_launch_types,
        'cluster_arn': run_environment.aws_ecs_default_cluster_arn,
        'execution_role': run_environment.aws_ecs_default_execution_role,
        'task_role': run_environment.aws_ecs_default_task_role,
        'platform_version': run_environment.aws_ecs_default_platform_version,
        'enable_ecs_managed_tags': run_environment.aws_ecs_enable_ecs_managed_tags
    })


def populate_run_environment_aws_ecs_configuration(run_environment: RunEnvironment) -> bool:
    if run_environment.aws_ecs_default_cluster_arn or run_environment.aws_ecs_default_execution_role:
        aws_ecs_config = extract_aws_ecs_configuration(run_environment)

        if aws_ecs_config:
            aws_ecs_settings = AwsEcsExecutionMethodSettings.parse_obj(
                    aws_ecs_config)
            aws_ecs_settings.update_derived_attrs()
            aws_ecs_config = aws_ecs_settings.dict()

        run_environment.default_aws_ecs_configuration = aws_ecs_config

        return True
    else:
        return False


def extract_emc(task: Task) -> dict[str, Any]:
    return convert_empty_to_none_values({
        'launch_type': task.aws_ecs_default_launch_type,
        'supported_launch_types': task.aws_ecs_supported_launch_types,
        'cluster_arn': task.aws_ecs_default_cluster_arn,
        'execution_role': task.aws_ecs_default_execution_role,
        'task_role': task.aws_ecs_default_task_role,
        'platform_version': task.aws_ecs_default_platform_version,
        'enable_ecs_managed_tags': task.aws_ecs_enable_ecs_managed_tags,
        'task_definition_arn': task.aws_ecs_task_definition_arn,
        'main_container_name': task.aws_ecs_main_container_name,
    })


def extract_infra_from_task(task: Task) -> dict[str, Any]:
    region = compute_region(task)

    log_stream_prefix: Optional[str] = None

    log_query = task.log_query
    if log_query:
        last_slash_index = log_query.rfind('/')
        if last_slash_index >= 0:
            log_stream_prefix = log_query[(last_slash_index + 1):]

    aws = {
        'region': region,
        'network': convert_empty_to_none_values({
            'region': region,
            'subnets': task.aws_default_subnets,
            'security_groups': task.aws_ecs_default_security_groups,
            'assign_public_ip': task.aws_ecs_default_assign_public_ip
        }),
        'logging': {
            'driver': 'awslogs',
            'options': {
                'region': region,
                'group': log_query,
                'create_group': 'true',
                'stream_prefix': log_stream_prefix
            }
        }
    }

    if task.aws_tags is not None:
        aws['tags'] = task.aws_tags

    return aws


def extract_scheduling_settings(task: Task) -> dict[str, Any]:
    return convert_empty_to_none_values({
        'execution_rule_name': task.aws_scheduled_execution_rule_name,
        'event_rule_arn': task.aws_scheduled_event_rule_arn,
        'event_target_rule_name': task.aws_event_target_rule_name,
        'event_target_id': task.aws_event_target_id,
        'event_bus_name': None
    })

def extract_load_balancer(lb) -> dict[str, Any]:
    return convert_empty_to_none_values({
        'target_group_arn': lb.target_group_arn,
        'container_name': lb.container_name,
        'container_port': lb.container_port
    })

def extract_service_settings(task: Task) -> dict[str, Any]:
    load_balancer_settings = None

    load_balancers = [lb for lb in AwsEcsServiceLoadBalancerDetails.objects.raw("""
        SELECT * FROM processes_awsecsserviceloadbalancerdetails
        WHERE process_type_id = %s
        """, [task.id])]

    if load_balancers:
        load_balancer_settings = {
            'health_check_grace_period_seconds': task.aws_ecs_service_load_balancer_health_check_grace_period_seconds,
            'load_balancers': [extract_load_balancer(lb) for lb in load_balancers],
        }

    mhp = 100
    if task.aws_ecs_service_deploy_minimum_healthy_percent is not None:
        mhp = task.aws_ecs_service_deploy_minimum_healthy_percent

    return convert_empty_to_none_values({
        'deployment_configuration': {
            'maximum_percent': task.aws_ecs_service_deploy_maximum_percent or 200,
            'minimum_healthy_percent': mhp,
            'deployment_circuit_breaker': {
                'enable': task.aws_ecs_service_deploy_enable_circuit_breaker or False,
                'rollback_on_failure': task.aws_ecs_service_deploy_rollback_on_failure or False,
            }
        },
        'load_balancer_settings': load_balancer_settings,
        'service_arn': task.aws_ecs_service_arn,
        'force_new_deployment': task.aws_ecs_service_force_new_deployment,
        'scheduling_strategy': 'REPLICA',
        'enable_ecs_managed_tags': task.aws_ecs_service_enable_ecs_managed_tags,
        'propagate_tags': task.aws_ecs_service_propagate_tags,
        'tags': task.aws_ecs_service_tags
    })


def populate_task_emc_and_infra(task: Task, should_reset: bool=False) -> bool:
    if task.execution_method_type == AwsEcsExecutionMethod.NAME:
        if should_reset or (task.execution_method_capability_details is None):
            task.execution_method_capability_details = extract_emc(task)

        task.infrastructure_type = INFRASTRUCTURE_TYPE_AWS

        if should_reset or (task.infrastructure_settings is None):
            task.infrastructure_settings = extract_infra_from_task(task)

        if should_reset or (task.service_settings is None):
            task.service_provider_type = ''
            task.service_settings = None
            task.is_service_managed = None

            if not task.passive and task.service_instance_count:
                task.service_provider_type = 'AWS ECS'
                task.service_settings = extract_service_settings(task)

                if task.enabled:
                    task.is_service_managed = True

        if should_reset or (task.scheduling_settings is None):
            task.scheduling_provider_type = ''
            task.scheduling_settings = None
            task.is_scheduling_managed = None

            if not task.passive and task.scheduled_instance_count and task.schedule:
                task.scheduling_provider_type = SCHEDULING_TYPE_AWS_CLOUDWATCH
                task.scheduling_settings = extract_scheduling_settings(task)

                if task.enabled:
                    task.is_scheduling_managed = True

        return True
    else:
        return False

def extract_em(task_execution: TaskExecution) -> dict[str, Any]:
    te = task_execution
    return convert_empty_to_none_values({
        'launch_type': te.aws_ecs_launch_type,
        'cluster_arn': te.aws_ecs_cluster_arn,
        'execution_role': te.aws_ecs_execution_role,
        'task_role': te.aws_ecs_task_role,
        'platform_version': te.aws_ecs_platform_version,
        'task_definition_arn': te.aws_ecs_task_definition_arn,
        'task_arn': te.aws_ecs_task_arn
    })


def extract_infra_from_task_execution(task_execution: TaskExecution) -> dict[str, Any]:
    te = task_execution
    task = te.task

    task_region = compute_region(task)

    log_stream_prefix: Optional[str] = None

    log_query = task.log_query
    if log_query:
        last_slash_index = log_query.rfind('/')
        if last_slash_index >= 0:
            log_stream_prefix = log_query[(last_slash_index + 1):]

    aws_defaults = {
        'region': task_region,
        'network': convert_empty_to_none_values({
            'region': task_region,
            'subnets': task.aws_default_subnets,
            'security_groups': task.aws_ecs_default_security_groups,
            'assign_public_ip': task.aws_ecs_default_assign_public_ip
        }),
        'logging': {
            'driver': 'awslogs',
            'options': {
                'region': task_region,
                'group': log_query,
                'create_group': 'true',
                'stream_prefix': log_stream_prefix
            }
        }
    }

    aws = {
        'network': convert_empty_to_none_values({
            'subnets': te.aws_subnets,
            'security_groups': te.aws_ecs_security_groups,
            'assign_public_ip': te.aws_ecs_assign_public_ip
        }),
        'tags': te.aws_tags
    }

    return deepmerge_with_lists(aws_defaults, te.infrastructure_settings or {}, aws)


def populate_task_execution_em_and_infra(task_execution: TaskExecution,
        should_reset: bool=False) -> bool:
    te = task_execution
    if te.aws_ecs_task_definition_arn:
        te.execution_method_type = AwsEcsExecutionMethod.NAME

        if should_reset or (te.execution_method_details is None):
            te.execution_method_details = extract_em(te)

        if not te.infrastructure_type:
            te.infrastructure_type = INFRASTRUCTURE_TYPE_AWS

        if should_reset or (not te.infrastructure_settings):
            te.infrastructure_settings = extract_infra_from_task_execution(te)

        return True
    else:
        return False
