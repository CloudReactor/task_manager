from typing import Any, Optional

import logging

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail
from rest_framework.fields import empty

from processes.serializers.base_execution_method_capability_serializer import BaseExecutionMethodCapabilitySerializer

from ..models import RunEnvironment, AwsEcsServiceLoadBalancerDetails

from .serializer_helpers import SerializerHelpers
from .base_aws_ecs_execution_method_serializer import (
    BaseAwsEcsExecutionMethodSerializer
)
from .aws_ecs_task_definition_serializer import AwsEcsTaskDefinitionSerializer
from .aws_ecs_service_options_serializer import AwsEcsServiceOptionsSerializer

logger = logging.getLogger(__name__)


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
                validated['aws_ecs_default_cluster_arn'] = 'arn:aws:ecs:' \
                        + self.run_environment.aws_default_region + ':' \
                        + self.run_environment.aws_account_id + ':cluster/' + cluster
            else:
                raise serializers.ValidationError({
                    'aws_ecs_default_cluster_arn': [
                        ErrorDetail('AWS ECS cluster ARN must be fully qualified', code='invalid')
                    ]
                })

        validated['aws_default_subnets'] = data.get('default_subnets')

        is_service = self.is_service

        service_dict = data.get('service_options')

        if service_dict:
            if is_service is None:
                is_service = True
                validated['is_service'] = True
            elif is_service is False:
                raise serializers.ValidationError({
                    'execution_method_capability.service_options': [
                        ErrorDetail('Must be blank or non-negative for services', code='invalid')
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

        return validated
