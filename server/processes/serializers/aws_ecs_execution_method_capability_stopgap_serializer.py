from typing import Any, Optional

import logging

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail
from rest_framework.fields import empty

from ..execution_methods import AwsEcsExecutionMethod
from ..models import RunEnvironment

from .serializer_helpers import SerializerHelpers
from .aws_ecs_task_definition_serializer import AwsEcsTaskDefinitionSerializer

logger = logging.getLogger(__name__)


class AwsEcsExecutionMethodCapabilityStopgapSerializer(
        SerializerHelpers,
        AwsEcsTaskDefinitionSerializer):
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

    cluster_arn = serializers.CharField(
            source='aws_ecs_default_cluster_arn',
            max_length=1000, required=False)

    main_container_name = serializers.CharField(
        source='aws_ecs_main_container_name', max_length=1000, required=False)

    execution_role = serializers.CharField(
            source='aws_ecs_default_execution_role', max_length=1000,
            required=False)

    task_role = serializers.CharField(
            source='aws_ecs_default_task_role', max_length=1000,
            required=False)

    platform_version = serializers.CharField(
            source='aws_ecs_default_platform_version', max_length=10,
            required=False)

    def __init__(self, instance=None, data=empty,
            run_environment: Optional[RunEnvironment] = None,
            **kwargs) -> None:
        super().__init__(instance, data, **kwargs)

        self.run_environment = run_environment

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        validated: dict[str, Any] = {
            'execution_method_capability_details': data
        }

        included_keys = []
        string_valued_columns = []

        for field_name, field_instance in self.get_fields().items():
            if not field_instance.read_only:
                included_keys.append(field_name)

                if (not field_instance.allow_null) and \
                        isinstance(field_instance, serializers.CharField):
                    string_valued_columns.append(field_instance.source or field_name)

        print(f"{string_valued_columns=}")

        default_prefixed_keys = ['execution_role', 'task_role', 'platform_version']

        validated = self.copy_props_with_prefix(dest_dict=validated,
                src_dict=data,
                dest_prefix='aws_ecs_',
                included_keys=included_keys,
                except_keys=default_prefixed_keys + ['cluster_arn'])

        validated = self.copy_props_with_prefix(dest_dict=validated,
                src_dict=data,
                dest_prefix='aws_ecs_default_',
                included_keys=default_prefixed_keys)

        for column_name in string_valued_columns:
            if column_name in validated:
                validated[column_name] = validated[column_name] or ''

        logger.info(f"After copy {validated=}")

        cluster = data.get('cluster_arn')

        if 'cluster_arn' in data:
            if cluster:
                if not cluster.startswith('arn:'):
                    if self.run_environment and \
                            self.run_environment.aws_default_region and  \
                            self.run_environment.aws_account_id:
                        cluster = 'arn:aws:ecs:' \
                                + self.run_environment.aws_default_region + ':' \
                                + self.run_environment.aws_account_id + ':cluster/' + cluster
                    else:
                        raise serializers.ValidationError({
                            'aws_ecs_default_cluster_arn': [
                                ErrorDetail('AWS ECS cluster ARN must be fully qualified', code='invalid')
                            ]
                        })

            validated['aws_ecs_default_cluster_arn'] = cluster or ''

        return validated
