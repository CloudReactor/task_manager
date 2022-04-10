from typing import cast, Any, Dict, Optional, Sequence

import logging

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, ParseError
from rest_framework.fields import empty

from drf_spectacular.utils import (
    extend_schema_field,
    # PolymorphicProxySerializer,
)

from ..common.request_helpers import (
  ensure_group_access_level,
  find_group_by_id_or_name, required_user_and_group_from_request,
)
from ..exception.unprocessable_entity import UnprocessableEntity
from ..execution_methods import *
from ..models import RunEnvironment, UserGroupAccessLevel

from .name_and_uuid_serializer import NameAndUuidSerializer
from .aws_ecs_run_environment_execution_method_capability_serializer import (
    AwsEcsRunEnvironmentExecutionMethodCapabilitySerializer
)
from .group_serializer import GroupSerializer
from .serializer_helpers import SerializerHelpers


logger = logging.getLogger(__name__)


class RunEnvironmentSerializer(SerializerHelpers,
        serializers.HyperlinkedModelSerializer):
    """
    RunEnvironments contain common settings for running a set of
    related Tasks. Usually RunEnvironments group Tasks in the same
    deployment environment (e.g. staging or production).
    Task and Workflows belong to a RunEnvironment but can override
    the RunEnvironment's settings.
    """

    class Meta:
        model = RunEnvironment
        fields = ['url', 'uuid', 'name', 'description', 'dashboard_url',
                  'created_by_user', 'created_by_group',
                  'created_at', 'updated_at', 'aws_account_id',
                  'aws_default_region', 'aws_access_key',
                  'aws_assumed_role_external_id', 'aws_events_role_arn',
                  'aws_workflow_starter_lambda_arn', 'aws_workflow_starter_access_key',
                  'default_alert_methods',
                  'execution_method_capabilities']

        read_only_fields = [
            'url', 'uuid', 'dashboard_url',
            'created_by_user', 'created_by_group',
            'created_at', 'updated_at'
        ]

    created_by_user = serializers.ReadOnlyField(source='created_by_user.username')
    created_by_group = GroupSerializer(read_only=True, include_users=False)
    url = serializers.HyperlinkedIdentityField(
        view_name='run_environments-detail',
        lookup_field='uuid'
    )
    execution_method_capabilities = serializers.SerializerMethodField()
    default_alert_methods = NameAndUuidSerializer(include_name=True,
            view_name='alert_methods-detail', required=False, many=True)

    SUMMARY_PROPS = set(['url', 'uuid', 'name', 'description', 'dashboard_url',
        'created_by_user', 'created_by_group',
        'created_at', 'updated_at', 'default_alert_methods',])

    def __init__(self, instance=None, data=empty, context: Optional[Dict[str, Any]] = None,
            forced_access_level: Optional[int] = None, **kwargs) -> None:
        context = context or {}

        # instance can either be a list of Run Environment or a single Run Environment
        # We assume the list has already pre-filtered so if the API key was only
        # for a single Run Environment, the list would only have a single
        # Run Environment.
        if instance and isinstance(instance, list):
            instance = instance[0]

        if instance:
            access_level = forced_access_level
            if access_level is None:
                _user, _group, access_level = ensure_group_access_level(
                        group=instance.created_by_group,
                        min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER,
                        run_environment=instance, allow_api_key=True,
                        request=context.get('request'))

            if access_level < UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER:
                for prop in (self.fields.keys() - self.SUMMARY_PROPS):
                    del self.fields[prop]

        super().__init__(instance, data, context=context, **kwargs)

    # TODO: use PolymorphicProxySerializer when it is supported
    @extend_schema_field(AwsEcsRunEnvironmentExecutionMethodCapabilitySerializer(many=True))
    def get_execution_method_capabilities(self, run_env: RunEnvironment) \
            -> Sequence[Dict[str, Any]]:
        rv = []
        if run_env.can_control_aws_ecs():
            rv.append(AwsEcsRunEnvironmentExecutionMethodCapabilitySerializer(
                    run_env).data)
        return rv

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # May be None
        group = find_group_by_id_or_name(obj_dict=data.pop('created_by_group', None),
                raise_exception_if_missing=False)

        validated = super().to_internal_value(data)
        validated['created_by_user'] = self.get_request_user()
        validated['created_by_group'] = group

        try:
            caps = data.get('execution_method_capabilities')

            if caps is not None:
                # TODO: clear existing properties
                found_cap_types: list[str] = []
                for cap in caps:
                    cap_type = cap['type']
                    found_cap_types.append(cap_type)
                    if cap_type == AwsEcsExecutionMethod.NAME:
                        validated = self.copy_aws_ecs_properties(validated, cap)
                    else:
                        raise serializers.ValidationError(f"Unknown execution method capability type '{cap_type}'")

                if AwsEcsExecutionMethod.NAME not in found_cap_types:
                    validated['aws_events_role_arn'] = ''

        except serializers.ValidationError as validation_error:
            self.handle_to_internal_value_exception(validation_error,
                                                    field_name='execution_environment_capabilities')

        self.set_validated_alert_methods(data=data, validated=validated,
            run_environment=cast(Optional[RunEnvironment], self.instance),
            property_name='default_alert_methods')

        return validated

    def create(self, validated_data):
        logger.info(f"create: validated_data = {validated_data}")
        request = self.context.get('request')
        alert_methods = validated_data.pop('default_alert_methods', None)

        _request_user, auth_group = required_user_and_group_from_request(
                request=request)

        group = validated_data.get('created_by_group')

        if group is None:
            group = auth_group
        else:
            if auth_group and (group.pk != auth_group.pk):
                raise UnprocessableEntity('Request body group does not match authenticated Group')

        if group is None:
            raise ParseError('Group is missing')

        # If API key is scoped to a specific Run Environment, this should fail
        ensure_group_access_level(group=group,
            min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            run_environment=None,
            request=request)

        validated_data['created_by_group'] = group

        run_environment = RunEnvironment.objects.create(**validated_data)

        if alert_methods is not None:
            run_environment.default_alert_methods.set(alert_methods)
            run_environment.save()

        return run_environment

    def update(self, instance: RunEnvironment, validated_data: Dict[str, Any]):
        request = self.context.get('request')
        alert_methods = validated_data.pop('default_alert_methods', None)

        _request_user, auth_group = required_user_and_group_from_request(
                request=request)

        group = validated_data.get('created_by_group') or instance.created_by_group

        if auth_group and (group.pk != auth_group.pk):
            raise UnprocessableEntity({
              'created_by_group': [
                  ErrorDetail('Request body group does not match authenticated Group',
                          'invalid')
              ]
            })

        validated_data['created_by_group'] = group

        if instance.created_by_group.pk != group.pk:
            raise UnprocessableEntity({
                'created_by_group': [
                    ErrorDetail(f"Can't change the group of an existing Run Environment {instance.pk=} {group.pk=}",
                            'invalid')
                ]
            })

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if alert_methods is not None:
            instance.default_alert_methods.set(alert_methods)
            instance.save()

        return instance

    def copy_aws_ecs_properties(self, validated: dict[str, Any],
          cap: dict[str, Any]) -> dict[str, Any]:
        self.copy_props_with_prefix(dest_dict=validated,
                                    src_dict=cap,
                                    dest_prefix='aws_ecs_',
                                    except_keys=['type', 'default_subnets'])

        aws_default_region = validated.get('aws_default_region')
        aws_account_id = validated.get('aws_account_id')

        if self.instance:
            existing_run_env = cast(RunEnvironment, self.instance)
            if not aws_default_region:
                aws_default_region = existing_run_env.aws_default_region
            if not aws_account_id:
                aws_account_id = existing_run_env.aws_account_id

        if not aws_default_region and not aws_account_id:
            raise serializers.ValidationError('AWS default region and AWS account ID must be specified if cluster name is not an ARN')

        cluster = validated.get('aws_ecs_default_cluster_arn')
        if cluster and not cluster.startswith('arn:'):
            validated['aws_ecs_default_cluster_arn'] = f"arn:aws:ecs:{aws_default_region}:{aws_account_id}:cluster/{cluster}"

        for p in ['aws_events_role_arn', 'aws_ecs_default_execution_role',
                'aws_ecs_default_task_role']:
            role = validated.get(p)
            if role and not role.startswith('arn:'):
                validated[p] = f'arn:aws:iam::{aws_account_id}:role/{role}'

        default_subnets = cap.get('default_subnets')
        if default_subnets is not None:
            validated['aws_default_subnets'] = default_subnets

        lambda_arn = validated['aws_workflow_starter_lambda_arn']
        if lambda_arn and not lambda_arn.startswith('arn:'):
            validated['aws_workflow_starter_lambda_arn'] = \
                    f'arn:aws:lambda:{aws_default_region}:{aws_account_id}:function:{lambda_arn}'

        return validated
