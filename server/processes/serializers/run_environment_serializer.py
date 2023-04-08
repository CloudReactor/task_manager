from typing import cast, Any, Optional, Sequence

import logging

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, ParseError
from rest_framework.fields import empty

from rest_flex_fields.serializers import FlexFieldsSerializerMixin

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


class RunEnvironmentSerializer(FlexFieldsSerializerMixin,
        SerializerHelpers,
        serializers.HyperlinkedModelSerializer):
    """
    RunEnvironments contain common settings for running a set of
    related Tasks. Usually RunEnvironments group Tasks in the same
    deployment environment (e.g. staging or production).
    Task and Workflows belong to a RunEnvironment but can override
    the RunEnvironment's settings.
    """

    DEFAULT_LABEL = '__default__'
    SETTINGS_KEY = 'settings'
    INFRASTRUCTURE_NAME_KEY = 'infrastructure_name'

    class Meta:
        model = RunEnvironment
        fields = [
            'url', 'uuid', 'name', 'description', 'dashboard_url',
            'created_by_user', 'created_by_group',
            'created_at', 'updated_at',
            'infrastructure_settings',
            'aws_account_id',
            'aws_default_region',
            'default_alert_methods',
            'execution_method_capabilities',
            'execution_method_settings',
        ]

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

    infrastructure_settings = serializers.SerializerMethodField()

    # Deprecated, maintained for compatibility with aws-ecs-cloudreactor-deployer
    aws_account_id = serializers.SerializerMethodField()
    aws_default_region = serializers.SerializerMethodField()
    execution_method_capabilities = serializers.SerializerMethodField()

    execution_method_settings = serializers.SerializerMethodField()

    default_alert_methods = NameAndUuidSerializer(include_name=True,
            view_name='alert_methods-detail', required=False, many=True)

    SUMMARY_PROPS = set(['url', 'uuid', 'name', 'description', 'dashboard_url',
        'created_by_user', 'created_by_group',
        'created_at', 'updated_at', 'default_alert_methods',])

    def __init__(self, instance=None, data=empty, context: Optional[dict[str, Any]] = None,
            forced_access_level: Optional[int] = None, **kwargs) -> None:
        context = context or {}

        super().__init__(instance, data, context=context, **kwargs)

        # instance can either be a list of Run Environments or a single Run Environment
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


    # Deprecated
    def get_aws_account_id(self, run_env: RunEnvironment) -> str:
        try:
            return run_env.infrastructure_settings[INFRASTRUCTURE_TYPE_AWS][self.DEFAULT_LABEL][self.SETTINGS_KEY]['account_id']
        except KeyError:
            return None
        except TypeError:
            return None

    # Deprecated
    def get_aws_default_region(self, run_env: RunEnvironment) -> str:
        try:
            return run_env.infrastructure_settings[INFRASTRUCTURE_TYPE_AWS][self.DEFAULT_LABEL][self.SETTINGS_KEY]['region']
        except KeyError:
            return None
        except TypeError:
            return None

    # Deprecated
    # TODO: use PolymorphicProxySerializer when it is supported
    @extend_schema_field(AwsEcsRunEnvironmentExecutionMethodCapabilitySerializer(many=True))
    def get_execution_method_capabilities(self, run_env: RunEnvironment) \
            -> Sequence[dict[str, Any]]:
        rv = []
        if run_env.can_control_aws_ecs():
            rv.append(AwsEcsRunEnvironmentExecutionMethodCapabilitySerializer(
                    run_env).data)
        return rv


    def get_infrastructure_settings(self, run_env: RunEnvironment) \
            -> dict[str, Any]:
        rv = {}
        if run_env.aws_settings:
            aws_settings_dict = run_env.aws_settings.copy()
            for p in PROTECTED_AWS_SETTINGS_PROPERTIES:
                aws_settings_dict.pop(p, None)

            rv[INFRASTRUCTURE_TYPE_AWS] = {
                self.DEFAULT_LABEL: {
                    self.SETTINGS_KEY: aws_settings_dict
                }
            }

        return rv


    def get_execution_method_settings(self, run_env: RunEnvironment) \
            -> dict[str, Any]:
        rv = {}
        if run_env.default_aws_ecs_configuration:
            capabilities: list[str] = []
            try:
                em = AwsEcsExecutionMethod(
                    aws_settings=run_env.aws_settings,
                    aws_ecs_settings=run_env.default_aws_ecs_configuration)
                capabilities = [c.name for c in em.capabilities()]
            except Exception:
                logger.warning("Can't compute capabilities for default ECS configuration")

            rv[AwsEcsExecutionMethod.NAME] = {
                self.DEFAULT_LABEL: {
                    self.SETTINGS_KEY: run_env.default_aws_ecs_configuration,
                    'capabilities': capabilities,
                    self.INFRASTRUCTURE_NAME_KEY: self.DEFAULT_LABEL
                }
            }

        return rv


    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        # May be None
        group = find_group_by_id_or_name(obj_dict=data.pop('created_by_group', None),
                raise_exception_if_missing=False)

        validated = super().to_internal_value(data)
        validated['created_by_user'] = self.get_request_user()
        validated['created_by_group'] = group

        infra_settings = data.get('infrastructure_settings')

        if infra_settings:
            name_to_aws_settings_container = infra_settings.get(INFRASTRUCTURE_TYPE_AWS)
            if name_to_aws_settings_container:
                for name, aws_settings_container in name_to_aws_settings_container.items():
                    if name == self.DEFAULT_LABEL:
                        aws_settings = aws_settings_container.get('settings')

                        if aws_settings is None:
                            logger.warning('No settings found inside default AWS settings container')
                        else:
                            validated['aws_settings'] = aws_settings

                            # Remove once RunEnvironmentSerializer gets these from aws_settings
                            self.copy_props_with_prefix(dest_dict=validated,
                                    src_dict=aws_settings,
                                    dest_prefix='aws_',
                                    included_keys=['account_id', 'default_region',
                                    'access_key', 'secret_key', 'events_role_arn',
                                    'assumed_role_external_id',
                                    'workflow_starter_lambda_arn',
                                    'workflow_starter_access_key',
                                    ], none_to_empty_strings=True)

                            default_aws_network = aws_settings.get('network')

                            if default_aws_network:
                                validated['aws_default_subnets'] = default_aws_network['subnets']
                                validated['aws_ecs_default_security_groups'] = default_aws_network['security_groups']
                                validated['aws_ecs_default_assign_public_ip'] = default_aws_network['assign_public_ip']
                    else:
                        raise serializers.ValidationError({
                            'infrastructure_settings': ['Non-default infrastructure settings not supported yet']
                        })

        em_defaults = data.get('execution_method_settings') or {}

        for emt, em_settings in em_defaults.items():
            for execution_method_name, meta_settings in em_settings.items():
                if execution_method_name == self.DEFAULT_LABEL:
                    meta_settings = meta_settings or {}

                    if (emt == AwsEcsExecutionMethod.NAME) or (emt == AwsLambdaExecutionMethod.NAME):
                        infrastructure_name = meta_settings.get(self.INFRASTRUCTURE_NAME_KEY)

                        if infrastructure_name and (infrastructure_name != self.DEFAULT_LABEL):
                            raise serializers.ValidationError({
                                'execution_method_settings': [f"Found {infrastructure_name=}, but only '{self.DEFAULT_LABEL}' is supported for now"]
                            })
                    elif emt:
                        raise serializers.ValidationError({
                            'execution_method_settings': [f"Unsupported execution method type: '{emt}'"]
                        })

                    em_settings = meta_settings.get(self.SETTINGS_KEY)

                    if em_settings:
                        if emt == AwsEcsExecutionMethod.NAME:
                            validated['default_aws_ecs_configuration'] = em_settings

                            # Remove after aws_settings becomes source of truth
                            self.copy_props_with_prefix(dest_dict=validated,
                                    src_dict=em_settings,
                                    dest_prefix='aws_ecs_default_',
                                    except_keys=['supported_launch_types', 'enable_ecs_managed_tags'])

                            self.copy_props_with_prefix(dest_dict=validated,
                                    src_dict=em_settings,
                                    dest_prefix='aws_ecs_',
                                    included_keys=['supported_launch_types', 'enable_ecs_managed_tags'])
                        elif emt == AwsLambdaExecutionMethod.NAME:
                            validated['default_aws_lambda_configuration'] = em_settings
                else:
                    raise serializers.ValidationError({
                        'execution_method_settings': [f"Found {execution_method_name=}, but only '{self.DEFAULT_LABEL}' is supported for now"],
                    })


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

    def update(self, instance: RunEnvironment, validated_data: dict[str, Any]):
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
