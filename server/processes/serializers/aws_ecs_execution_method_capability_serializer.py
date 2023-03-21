from typing import Any, Optional

import logging

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail
from rest_framework.fields import empty

from ..models import RunEnvironment, AwsEcsServiceLoadBalancerDetails
from ..models.convert_legacy_em_and_infra import convert_empty_to_none_values
from ..execution_methods.aws_settings import INFRASTRUCTURE_TYPE_AWS
from ..execution_methods.aws_ecs_execution_method import (
    AwsEcsExecutionMethod, SERVICE_PROVIDER_AWS_ECS
)

from .serializer_helpers import SerializerHelpers
from .base_execution_method_capability_serializer import (
    BaseExecutionMethodCapabilitySerializer
)
from .base_aws_ecs_execution_method_serializer import (
    BaseAwsEcsExecutionMethodSerializer
)
from .aws_ecs_task_definition_serializer import AwsEcsTaskDefinitionSerializer
from .aws_ecs_service_options_serializer import AwsEcsServiceOptionsSerializer

logger = logging.getLogger(__name__)

# Deprecated
class AwsEcsExecutionMethodCapabilitySerializer(
        SerializerHelpers,
        AwsEcsTaskDefinitionSerializer,
        BaseAwsEcsExecutionMethodSerializer,
        BaseExecutionMethodCapabilitySerializer):
    main_container_name = serializers.CharField(
        source='aws_ecs_main_container_name', max_length=1000, required=False)
    service_options = AwsEcsServiceOptionsSerializer(source='*', required=False)


    def __init__(self, instance=None, data=empty,
            run_environment: Optional[RunEnvironment] = None,
            is_service: Optional[bool] = None,
            **kwargs) -> None:
        super().__init__(instance, data, **kwargs)

        self.run_environment = run_environment
        self.is_service = is_service

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        validated: dict[str, Any] = {}

        included_keys = self.get_fields().keys()

        validated = self.copy_props_with_prefix(dest_dict=validated,
                src_dict=data, included_keys=[
                    'allocated_cpu_units', 'allocated_memory_mb',
                ])

        validated = self.copy_props_with_prefix(dest_dict=validated,
                src_dict=data,
                dest_prefix='aws_',
                included_keys=[
                    'tags'
                ])

        validated = self.copy_props_with_prefix(dest_dict=validated,
                src_dict=data,
                dest_prefix='aws_ecs_',
                included_keys=included_keys,
                except_keys=[
                    'type', 'allocated_cpu_units', 'allocated_memory_mb',
                    'default_subnets', 'service_options', 'tags'
                ])

        logger.info(f"After copy {validated=}")

        cluster = validated.get('aws_ecs_default_cluster_arn')
        if cluster and not cluster.startswith('arn:'):
            if self.run_environment:
                cluster = 'arn:aws:ecs:' \
                        + self.run_environment.aws_default_region + ':' \
                        + self.run_environment.aws_account_id + ':cluster/' + cluster
                validated['aws_ecs_default_cluster_arn'] = cluster
            else:
                raise serializers.ValidationError({
                    'aws_ecs_default_cluster_arn': [
                        ErrorDetail('AWS ECS cluster ARN must be fully qualified', code='invalid')
                    ]
                })

        validated['aws_default_subnets'] = data.get('default_subnets')
        validated['execution_method_type'] = AwsEcsExecutionMethod.NAME

        emcd: dict[str, Any] = convert_empty_to_none_values({
            'launch_type': data.get('default_launch_type'),
            'cluster_arn': cluster,
            'task_definition_arn': data.get('task_definition_arn'),
            'main_container_name': data.get('main_container_name'),
            'execution_role_arn': data.get('default_execution_role'),
            'task_role_arn': data.get('default_task_role'),
            'platform_version': data.get('default_platform_version'),
        })

        if 'tags' in data:
            emcd['tags'] = data['tags']

        if 'supported_launch_types' in data:
            emcd['supported_launch_types'] = data['supported_launch_types']

        validated['execution_method_capability_details'] = emcd

        validated['infrastructure_type'] = INFRASTRUCTURE_TYPE_AWS
        validated['infrastructure_settings'] = {
            'network': {
                'security_groups': data.get('default_security_groups'),
                'subnets': data.get('default_subnets'),
                'assign_public_ip': data.get('default_assign_public_ip')
            }
        }

        is_service = self.is_service

        service_dict = data.get('service_options')

        if service_dict:
            if is_service is None:
                is_service = True
                validated['is_service'] = True
            elif is_service is False:
                raise serializers.ValidationError({
                    'execution_method_capability.service_options': [
                        ErrorDetail('Must be empty for non-services', code='invalid')
                    ]
                })

            self.copy_props_with_prefix(dest_dict=validated,
                    src_dict=service_dict,
                    dest_prefix='aws_ecs_service_',
                    except_keys=['load_balancers'])

            load_balancer_dicts = service_dict.get('load_balancers')

            if load_balancer_dicts is not None:
                load_balancer_details_list = []
                for load_balancer_dict in load_balancer_dicts:
                    load_balancer_details_list.append(AwsEcsServiceLoadBalancerDetails(
                        task=None,
                        target_group_arn=load_balancer_dict['target_group_arn'],
                        container_name=load_balancer_dict.get('container_name', ''),
                        container_port=load_balancer_dict['container_port'],
                    ))

                validated['aws_ecs_load_balancer_details_set'] = load_balancer_details_list

            service_settings: dict[str, Any] = {}

            self.copy_props_with_prefix(dest_dict=service_settings,
                    src_dict=service_dict,
                    included_keys=[
                        'force_new_deployment',
                        'enabled_ecs_managed_tags',
                        'propagate_tags',
                        'tags'
                    ])

            service_settings['deployment_configuration'] = {
                'maximum_percent': service_dict.get('deploy_maximum_percent'),
                'minimum_healthy_percent': service_dict.get('deploy_minimum_healthy_percent'),
                'deployment_circuit_breaker': {
                    'enable': service_dict.get('deploy_enable_circuit_breaker'),
                    'rollback_on_failure': service_dict.get('deploy_rollback_on_failure'),
                }
            }

            if load_balancer_dicts is not None:
                service_settings['load_balancer_settings'] = {
                    'health_check_grace_period_seconds': service_dict.get('load_balancer_health_check_grace_period_seconds'),
                    'load_balancers': load_balancer_dicts
                }

            validated['service_settings'] = service_settings

        if is_service:
            validated['service_provider_type'] = SERVICE_PROVIDER_AWS_ECS
        elif is_service is False:
            validated['service_provider_type'] = ''

        return validated
