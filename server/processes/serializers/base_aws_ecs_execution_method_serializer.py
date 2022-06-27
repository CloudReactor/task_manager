from rest_framework import serializers

from ..models.run_environment import RunEnvironment

from ..execution_methods import AwsEcsExecutionMethod

from .base_execution_method_capability_serializer import (
    BaseExecutionMethodCapabilitySerializer
)

class BaseAwsEcsExecutionMethodSerializer(
        BaseExecutionMethodCapabilitySerializer):
    tags = serializers.HStoreField(source='aws_tags', allow_null=True,
            allow_empty=True, required=False)

    default_subnets = serializers.ListField(
            source='aws_default_subnets',
            child=serializers.CharField(max_length=1000), allow_null=True,
            allow_empty=False, required=False)
    default_subnet_infrastructure_website_urls = serializers.ListField(
            source='aws_subnet_infrastructure_website_urls',
            child=serializers.CharField(), read_only=True)

    default_launch_type = serializers.ChoiceField(
            source='aws_ecs_default_launch_type',
            choices=AwsEcsExecutionMethod.ALL_LAUNCH_TYPES,
            default=AwsEcsExecutionMethod.DEFAULT_LAUNCH_TYPE,
            allow_blank=True)

    supported_launch_types = serializers.ListField(
            source='aws_ecs_supported_launch_types',
            child=serializers.ChoiceField(choices=AwsEcsExecutionMethod.ALL_LAUNCH_TYPES,
                    default=AwsEcsExecutionMethod.DEFAULT_LAUNCH_TYPE),
            allow_null=True, allow_empty=False, required=False)

    default_cluster_arn = serializers.CharField(
            source='aws_ecs_default_cluster_arn',
            max_length=1000, required=False)
    default_cluster_infrastructure_website_url = serializers.CharField(
            source='aws_ecs_cluster_infrastructure_website_url',
            read_only=True)

    default_security_groups = serializers.ListField(
            source='aws_ecs_default_security_groups',
            child=serializers.CharField(max_length=1000),
            allow_null=True, allow_empty=False, required=False)
    default_security_group_infrastructure_website_urls = serializers.ListField(
            source='aws_security_group_infrastructure_website_urls',
            child=serializers.CharField(), read_only=True)

    default_assign_public_ip = serializers.BooleanField(
            source='aws_ecs_default_assign_public_ip',
            allow_null=True, required=False)

    default_execution_role = serializers.CharField(
            source='aws_ecs_default_execution_role', max_length=1000,
            required=False)
    default_execution_role_infrastructure_website_url = serializers.CharField(
            source='aws_ecs_execution_role_infrastructure_website_url',
            read_only=True)

    default_task_role = serializers.CharField(
            source='aws_ecs_default_task_role', max_length=1000,
            required=False)

    default_task_role_infrastructure_website_url = serializers.CharField(
            source='aws_ecs_task_role_infrastructure_website_url',
            read_only=True)

    default_platform_version = serializers.CharField(
            source='aws_ecs_default_platform_version', max_length=10,
            required=False)

    def get_execution_method_type(self, run_env: RunEnvironment) -> str:
        return AwsEcsExecutionMethod.NAME
