from typing import Any

from rest_framework import serializers

from ..execution_methods import AwsEcsExecutionMethod
from ..models import Task, AwsEcsServiceLoadBalancerDetails

from .serializer_helpers import SerializerHelpers
from .aws_ecs_service_load_balancer_details_serializer import AwsEcsServiceLoadBalancerDetailsSerializer

class AwsEcsServiceOptionsSerializer(SerializerHelpers, serializers.Serializer):
    """
    Options for running a Task as a service in AWS ECS.
    """

    load_balancers = AwsEcsServiceLoadBalancerDetailsSerializer(many=True, read_only=True,
            source='aws_ecs_service_load_balancer_details_set')

    health_check_grace_period_seconds = serializers.IntegerField(
            source='aws_ecs_service_load_balancer_health_check_grace_period_seconds',
            required=False)

    force_new_deployment = serializers.BooleanField(
            source='aws_ecs_service_force_new_deployment', required=False)

    deploy_minimum_healthy_percent = serializers.IntegerField(
            source='aws_ecs_service_deploy_minimum_healthy_percent',
            required=False)

    deploy_maximum_percent = serializers.IntegerField(
            source='aws_ecs_service_deploy_maximum_percent',
            required=False)

    deploy_enable_circuit_breaker = serializers.BooleanField(
            source='aws_ecs_service_deploy_enable_circuit_breaker',
            required=False)

    deploy_rollback_on_failure = serializers.BooleanField(
            source='aws_ecs_service_deploy_rollback_on_failure',
            required=False)

    enable_ecs_managed_tags = serializers.BooleanField(
            source='aws_ecs_service_enable_ecs_managed_tags', required=False)

    propagate_tags = serializers.ChoiceField(
            source='aws_ecs_service_propagate_tags',
            choices=AwsEcsExecutionMethod.SERVICE_PROPAGATE_TAGS_CHOICES,
            required=False, allow_blank=True)

    tags = serializers.HStoreField(source='aws_ecs_service_tags',
            allow_null=True, allow_empty=True, required=False)

    def to_representation(self, instance: Task):
        if instance.is_service:
            return super().to_representation(instance)

        return None

    def to_internal_value(self, data):
        validated: dict[str, Any] = {}

        self.copy_props_with_prefix(dest_dict=validated,
                src_dict=data,
                dest_prefix='aws_ecs_service_',
                included_keys=['force_new_deployment',
                    'enable_ecs_managed_tags', 'propagate_tags', 'tags'])

        deployment_configuration = data.get('deployment_configuration')
        if deployment_configuration is not None:
            self.copy_props_with_prefix(dest_dict=validated,
                    src_dict=deployment_configuration,
                    dest_prefix='aws_ecs_service_deploy_',
                    included_keys=['maximum_percent', 'minimum_healthy_percent'])

            dcb = deployment_configuration.get('deployment_circuit_breaker')
            if dcb is not None:
                self.copy_props_with_prefix(dest_dict=validated,
                    src_dict=dcb,
                    dest_prefix='aws_ecs_service_deploy_',
                    included_keys=['rollback_on_failure'])

                enable_dcb = dcb.get('enable')
                if enable_dcb is not None:
                    validated['aws_ecs_service_deploy_enable_circuit_breaker'] = enable_dcb

        load_balancer_settings = data.get('load_balancer_settings')

        if load_balancer_settings is not None:
            self.copy_props_with_prefix(dest_dict=validated,
                    src_dict=load_balancer_settings,
                    dest_prefix='aws_ecs_service_load_balancer_',
                    included_keys=['health_check_grace_period_seconds'])

            load_balancer_dicts = load_balancer_settings.get('load_balancers')

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
