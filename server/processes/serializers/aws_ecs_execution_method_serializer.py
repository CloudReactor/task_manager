from typing import Optional

from rest_framework import serializers

from ..execution_methods import AwsEcsExecutionMethod

from .base_execution_method_serializer import BaseExecutionMethodSerializer
from .aws_ecs_task_definition_serializer import AwsEcsTaskDefinitionSerializer

class AwsEcsExecutionMethodSerializer(BaseExecutionMethodSerializer,
        AwsEcsTaskDefinitionSerializer):
    """
    AwsEcsExecutionMethods contain configuration for running Tasks in
    AWS ECS.
    """

    tags = serializers.HStoreField(source='aws_tags', allow_null=True,
            allow_empty=True)

    subnets = serializers.ListField(
            source='aws_subnets',
            child=serializers.CharField(max_length=1000), allow_empty=False,
            required=False)
    subnet_infrastructure_website_urls = serializers.SerializerMethodField()

    security_groups = serializers.ListField(
            source='aws_ecs_security_groups',
            child=serializers.CharField(max_length=1000), allow_empty=False,
            required=False)
    security_group_infrastructure_website_urls = serializers.SerializerMethodField()

    assign_public_ip = serializers.BooleanField(
            source='aws_ecs_assign_public_ip', required=False)

    task_arn = serializers.CharField(source='aws_ecs_task_arn',
            max_length=1000, required=False)

    launch_type = serializers.ChoiceField(
            source='aws_ecs_launch_type',
            choices=AwsEcsExecutionMethod.ALL_LAUNCH_TYPES,
            default=AwsEcsExecutionMethod.DEFAULT_LAUNCH_TYPE)

    cluster_arn = serializers.CharField(
            source='aws_ecs_cluster_arn',
            max_length=1000, required=False)
    cluster_infrastructure_website_url = serializers.CharField(
            source='aws_ecs_cluster_infrastructure_website_url',
            read_only=True)

    execution_role = serializers.CharField(
            source='aws_ecs_execution_role', max_length=1000, required=False)
    execution_role_infrastructure_website_url = serializers.CharField(
            source='aws_ecs_execution_role_infrastructure_website_url',
            read_only=True)

    task_role = serializers.CharField(
        source='aws_ecs_task_role', max_length=1000, required=False)
    task_role_infrastructure_website_url = serializers.CharField(
            source='aws_ecs_task_role_infrastructure_website_url',
            read_only=True)

    platform_version = serializers.CharField(
            source='aws_ecs_platform_version',
            max_length=10, required=False)

    def get_execution_method_type(self, obj) -> str:
        return AwsEcsExecutionMethod.NAME

    def get_subnet_infrastructure_website_urls(self, te) \
            -> Optional[list[Optional[str]]]:
        return te.aws_subnet_infrastructure_website_urls

    def get_security_group_infrastructure_website_urls(self, te) \
            -> Optional[list[Optional[str]]]:
        return te.aws_security_group_infrastructure_website_urls
