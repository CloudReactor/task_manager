import logging

from typing import Any, Optional

from .task import Task
from .aws_ecs_service_load_balancer_details import AwsEcsServiceLoadBalancerDetails

logger = logging.getLogger(__name__)


def convert_empty_to_none_values(d: dict[str, Any]) -> dict[str, Any]:
    return { k: (None if v == '' else v) for (k, v) in d }


def compute_region_from_ecs_cluster_arn(
    cluster_arn: str
) -> Optional[str]:
    if not cluster_arn:
        return None

    if cluster_arn.startswith("arn:aws:ecs:"):
        parts = cluster_arn.split(":")
        return parts[3]

    logger.warning(f"Can't determine AWS region from cluster ARN '{cluster_arn}'")
    return None

def extract_emc(task) -> dict[str, Any]:
    return convert_empty_to_none_values({
        'default_launch_type': task.aws_ecs_default_launch_type,
        'supported_launch_types': task.aws_ecs_supported_launch_types,
        'cluster_arn': task.aws_ecs_default_cluster_arn,
        'execution_role': task.aws_ecs_default_execution_role,
        'task_role': task.aws_ecs_default_task_role,
        'platform_version': task.aws_ecs_default_platform_version,
        'enable_ecs_managed_tags': task.aws_ecs_enable_ecs_managed_tags,
        'task_definition_arn': task.aws_ecs_task_definition_arn,
        'main_container_name': task.aws_ecs_main_container_name,
    } )

def extract_infra(task) -> dict[str, Any]:
    region = compute_region_from_ecs_cluster_arn(
            task.aws_ecs_default_cluster_arn)
    return {
        'network': convert_empty_to_none_values({
            'region': region,
            'subnets': task.aws_default_subnets,
            'security_groups': task.aws_ecs_default_security_groups,
            'assign_public_ip': task.aws_ecs_default_assign_public_ip,
        }),
    }

def extract_scheduling_settings(task) -> dict[str, Any]:
    return convert_empty_to_none_values({
        'execution_rule_name': task.aws_scheduled_execution_rule_name,
        'event_rule_arn': task.aws_event_rule_arn,
        'event_target_rule_arn': task.aws_event_target_rule_arn,
        'event_target_id': task.aws_event_target_id,

    })

def extract_load_balancer(lb) -> dict[str, Any]:
    return convert_empty_to_none_values({
        'target_group_arn': lb.target_group_arn,
        'container_name': lb.container_name,
        'container_port': lb.container_port,
    })

def extract_service_settings(task) -> dict[str, Any]:
    load_balancer_settings = None

    load_balancers = [lb for lb in AwsEcsServiceLoadBalancerDetails.objects.raw("""
        SELECT * FROM processes_aws_ecs_service_load_balancer_details
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
                'rollback': task.aws_ecs_service_deploy_rollback_on_failure or False,
            }
        },
        'load_balancer_settings': load_balancer_settings,
        'service_arn': task.aws_ecs_service_arn,
        'force_new_deployment': task.force_new_deployment,
        'scheduling_strategy': 'REPLICA',
        'enable_ecs_managed_tags': task.aws_ecs_service_enable_ecs_managed_tags,
        'propagate_tags': task.aws_ecs_service_propagate_tags,
        'tags': task.aws_ecs_service_tags,
    })


def populate_task_emc_and_infra(apps, schema_editor):
    for task in Task.objects.all():
        if task.execution_method_type == 'AWS ECS':
            task.execution_method_capability = extract_emc(task)
            task.infrastructure_provider_type = 'AWS'
            task.infrastructure_settings = extract_infra(task)

            if task.aws_scheduled_execution_rule_name:
                task.scheduling_provider_type = 'AWS CloudWatch'
                task.scheduling_settings = extract_scheduling_settings(task)

            if task.aws_ecs_service_arn:
                task.service_provider_type = 'AWS ECS'
                task.service_settings = extract_service_settings(task)

            task.save()
