from rest_framework import serializers

from ..execution_methods import AwsEcsExecutionMethod

from .aws_ecs_service_load_balancer_details_serializer import AwsEcsServiceLoadBalancerDetailsSerializer
from ..models import Task

class AwsEcsServiceOptionsSerializer(serializers.Serializer):
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
