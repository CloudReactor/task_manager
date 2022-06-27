from rest_framework import serializers

from ..common.aws import *


class AwsEcsTaskDefinitionSerializer(serializers.Serializer):
    task_definition_arn = serializers.CharField(
            source='aws_ecs_task_definition_arn', max_length=1000,
            required=False)

    task_definition_infrastructure_website_url = serializers.CharField(
            source='aws_ecs_task_definition_infrastructure_website_url',
            read_only=True)

    allocated_cpu_units = serializers.IntegerField(required=False)
    allocated_memory_mb = serializers.IntegerField(required=False)
