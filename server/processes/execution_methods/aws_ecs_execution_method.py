from __future__ import annotations

from typing import Any, FrozenSet, Literal, TYPE_CHECKING, cast, override

from dataclasses import Field, dataclass
import logging
import random
import re
import string
import uuid

from django.utils import timezone

from rest_framework.exceptions import APIException

from pydantic import Field

from botocore.exceptions import ClientError

from processes.common.pydantic_settings_model import EXCLUDE_IF_NONE

from ..common import PydanticSettingsModel, coalesce, deepmerge
from ..common.aws import *
from ..exception.unprocessable_entity import UnprocessableEntity
from .aws_settings import INFRASTRUCTURE_TYPE_AWS, AwsNetworkSettings, AwsSettings, AwsTagKeyValuePair
from .aws_cloudwatch_scheduling_settings import (
    SCHEDULING_TYPE_AWS_CLOUDWATCH,
    AwsCloudwatchSchedulingSettings
)
from .aws_base_execution_method import AwsBaseExecutionMethod, AwsSubSettingsWithRole, Boto3SerializableSettings

if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )

from .execution_method import ExecutionMethod, ExecutionMethodSettings


logger = logging.getLogger(__name__)


SERVICE_PROVIDER_AWS_ECS = 'AWS ECS'

AWS_ECS_PLATFORM_VERSION_DEFAULT = '1.4.0'
AWS_ECS_PLATFORM_VERSION_LATEST = 'LATEST'


DEFAULT_MAIN_CONTAINER_NAME = 'main'

# Valid ECS launch types
LAUNCH_TYPE_EC2 = 'EC2'
LAUNCH_TYPE_FARGATE = 'FARGATE'
LAUNCH_TYPE_EXTERNAL = 'EXTERNAL'
ALL_LAUNCH_TYPES = [LAUNCH_TYPE_FARGATE, LAUNCH_TYPE_EC2, LAUNCH_TYPE_EXTERNAL]

PROPAGATE_TAGS_TASK_DEFINITION = 'TASK_DEFINITION'
PROPAGATE_TAGS_SERVICE = 'SERVICE'

DEFAULT_SCHEDULING_STRATEGY = 'REPLICA'
DEFAULT_ACCESS_LOG_FORMAT = 'TEXT'

def extract_ecs_cluster_name(ecs_cluster_arn: str | None) -> str | None:
    if not ecs_cluster_arn:
        return None

    try:
        last_slash_index = ecs_cluster_arn.rfind('/')
        return ecs_cluster_arn[last_slash_index+1:]
    except Exception:
        logger.error(f'Failed to compute cluster name for ARN {ecs_cluster_arn}',
                exc_info=True)
        return None


def make_aws_console_ecs_cluster_url(ecs_cluster_arn: str | None) -> str | None:
    if not ecs_cluster_arn:
        return None

    cluster_name = extract_ecs_cluster_name(ecs_cluster_arn)

    if not cluster_name:
        logger.error(f'Failed to compute AWS console URL for ARN {ecs_cluster_arn}: no cluster name',
                exc_info=True)
        return None

    try:
        parts = ecs_cluster_arn.split(':')
        region = parts[3]
        return make_regioned_aws_console_base_url(region) + ECS_HOME_PATH + \
                '?' + make_region_parameter(region) + '#/clusters/' + quote(cluster_name) + \
                '/tasks'
    except Exception:
        logger.error(f'Failed to compute AWS console URL for ARN {ecs_cluster_arn}',
                exc_info=True)

    return None

def make_aws_console_ecs_task_definition_url(task_definition_arn: str | None) -> str | None:
    if not task_definition_arn:
        return None

    try:
        parts = task_definition_arn.split(':')
        region = parts[3]
        version_number = parts[-1]
        middle = parts[-2]
        slash_index = middle.index('/')
        task_name = middle[slash_index+1:]

        return make_regioned_aws_console_base_url(region) + ECS_HOME_PATH + \
                '?' + make_region_parameter(region) + '#/taskDefinitions/' + quote(task_name) + \
                '/' + version_number
    except Exception:
        logger.error(f'Failed to compute AWS console URL for ARN {task_definition_arn}',
                exc_info=True)

    return None

def make_aws_console_ecs_service_url(ecs_service_arn: str | None,
        cluster_name: str | None = None):
    if not ecs_service_arn:
        return None

    # ECS Service ARN has old format:
    # arn:aws:ecs:[region]:[aws_account_id]:service/[service_name]

    # ECS Service ARN has new format:
    # arn:aws:ecs:[region]:[aws_account_id]:service/[cluster_name]/[service_name]

    # AWS Console URL has format:
    # https://us-east-2.console.aws.amazon.com/ecs/home?region=us-east-2#/clusters/[cluster_name]/services/[service_name]/details

    try:
        parts = ecs_service_arn.split(':')
        region = parts[3]
        last_part = parts[5]

        last_part_parts = last_part.split('/')
        if len(last_part_parts) < 3:
            if not cluster_name:
                logger.warning('Service ARN is old format and no cluster name given, returning None')
                return None
            service_name = last_part_parts[1]
        else:
            cluster_name = last_part_parts[1]
            service_name = last_part_parts[2]

        return make_regioned_aws_console_base_url(region) + ECS_HOME_PATH \
                + '?' + make_region_parameter(region) + '#/clusters/' \
                + quote(cluster_name) + '/services/' \
                + quote(service_name) + '/details'
    except Exception:
        logger.error(f'Failed to compute AWS console URL for ECS Service ARN {ecs_service_arn}',
                exc_info=True)

    return None

# Type aliases for valid ECS configuration values
LaunchType = Literal['EC2', 'FARGATE', 'EXTERNAL']
PropagateTags = Literal['TASK_DEFINITION', 'SERVICE', 'NONE']
PlatformVersion = Literal['1.4.0', 'LATEST']
SchedulingStrategy = Literal['REPLICA', 'DAEMON']
DeploymentConfigurationStrategy = Literal['ROLLING', 'BLUE_GREEN', 'LINEAR', 'CANARY']
AvailabilityZoneRebalancing = Literal['ENABLED', 'DISABLED']
LifecycleStage = Literal['RECONCILE_SERVICE', 'PRE_SCALE_UP', 'POST_SCALE_UP', 
    'TEST_TRAFFIC_SHIFT', 'POST_TEST_TRAFFIC_SHIFT', 'PRODUCTION_TRAFFIC_SHIFT']
ServiceConnectLogDriver = Literal['json-file', 'syslog', 'journald', 'gelf', 'fluentd', 'awslogs', 'splunk', 'awsfirelens']
AccessLogFormat = Literal['TEXT', 'JSON']
AccessLogIncludeQueryParameters = Literal['DISABLED', 'ENABLED']
FilesystemType = Literal['ext3', 'ext4', 'xfs', 'ntfs']
VolumeTagPropagation = Literal['TASK_DEFINITION', 'SERVICE', 'NONE']
ResourceManagementType = Literal['CUSTOMER', 'ECS']

class ContainerSettings(PydanticSettingsModel):
    name: str | None = None
    docker_id: str | None = None
    docker_name: str | None = None
    image_name: str | None = None
    image_id: str | None = None
    labels: dict[str, str] | None = None
    container_arn: str | None = None


class CapacityProviderStrategyItem(Boto3SerializableSettings):
    capacity_provider: str
    weight: int | None = None
    base: int | None = None

class AwsEcsCommonSettings(PydanticSettingsModel):
    launch_type: LaunchType | None = None
    cluster_arn: str | None = None
    cluster_infrastructure_website_url: str | None = Field(default=None, exclude_if=EXCLUDE_IF_NONE)
    task_definition_arn: str | None = None
    task_definition_infrastructure_website_url: str | None = \
            Field(default=None, exclude_if=EXCLUDE_IF_NONE)
    execution_role_arn: str | None = None
    execution_role_infrastructure_website_url: str | None = Field(default=None, exclude_if=EXCLUDE_IF_NONE)
    task_role_arn: str | None = None
    task_role_infrastructure_website_url: str | None = \
            Field(default=None, exclude_if=EXCLUDE_IF_NONE)
    platform_version: PlatformVersion | None = None
    capacity_provider_strategy: list[CapacityProviderStrategyItem] | None = None
    task_group: str | None = None    
    propagate_tags: PropagateTags | None = None
    enable_ecs_managed_tags: bool | None = None
    enable_execute_command: bool | None = None

    def boto3_capacity_provider_strategy_value(self) -> list[dict[str, Any]] | None:
        if self.capacity_provider_strategy is None:
            return None
        
        return [cpsi.to_boto3_dict() for cpsi in self.capacity_provider_strategy]
    

    def sanitize(self, aws_settings: AwsSettings | None) -> bool:        
        if aws_settings is None:
            logger.warning("Can't sanitize AwsEcsCommonSettings because aws_settings is None")
            return False

        changed = False

        cluster = self.cluster_arn

        if cluster and (not cluster.startswith('arn:')):
            account_id = aws_settings.account_id
            region = aws_settings.region
            if account_id and region:
                self.cluster_arn = f"arn:aws:ecs:{region}:{account_id}:cluster/{cluster}"
                changed = True
            else:
                logger.warning("Can't sanitize cluster ARN because aws_settings is missing account_id or region")

        return changed

    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        if aws_settings:
            aws_account_id = aws_settings.account_id
            region = aws_settings.region

            if aws_account_id and region:
                if self.cluster_arn and not self.cluster_arn.startswith('arn:'):
                    self.cluster_arn = 'arn:aws:ecs:' + region + ':' + \
                        aws_account_id + ':cluster/' + self.cluster_arn

                if self.execution_role_arn:
                    self.execution_role_arn = normalize_role_arn(self.execution_role_arn,
                            aws_account_id=aws_account_id)

                if self.task_role_arn:
                    self.task_role_arn = normalize_role_arn(self.task_role_arn,
                            aws_account_id=aws_account_id)

        self.cluster_infrastructure_website_url = \
            make_aws_console_ecs_cluster_url(self.cluster_arn)

        self.task_definition_infrastructure_website_url = \
            make_aws_console_ecs_task_definition_url(self.task_definition_arn)

        # Just a copy of the task definition URL, overwritten by
        # AwsEcsExecutionMethodInfo.update_derived_attrs()
        self.infrastructure_website_url = self.task_definition_infrastructure_website_url

        self.execution_role_infrastructure_website_url = \
            make_aws_console_role_url(self.execution_role_arn)

        self.task_role_infrastructure_website_url = \
            make_aws_console_role_url(self.task_role_arn)


class AwsEcsExecutionMethodSettings(ExecutionMethodSettings, AwsEcsCommonSettings):
    supported_launch_types: list[LaunchType] | None = None
    main_container_name: str | None = None
    main_container_cpu_units: int | None = None
    main_container_memory_mb: int | None = None
    monitor_container_name: str | None = None

    # Might not be sent during deployment, so use main_container_xxx properties
    containers: list[ContainerSettings] | None = None

class AwsEcsExecutionMethodInfo(AwsEcsExecutionMethodSettings):
    task_arn: str | None = None

    def update_derived_attrs(self, aws_settings: AwsSettings | None):
        super().update_derived_attrs(aws_settings=aws_settings)
        self.infrastructure_website_url = self.make_aws_console_url()

    def make_aws_console_url(self) -> str | None:
        if self.task_arn and self.cluster_arn:
            parts = self.task_arn.split(':')
            aws_region = parts[3]

            if not aws_region:
                return None
            
            last_part = parts[5]
            last_part_parts = last_part.split('/')
            if len(last_part_parts) < 3:
                cluster_name = extract_ecs_cluster_name(self.cluster_arn)
                task_id = last_part_parts[1]
            else:
                cluster_name = last_part_parts[1]
                task_id = last_part_parts[2]

            if cluster_name is None:
                logger.warning("Task.infrastructure_website_url() can't determine cluster_name")
                return None
            
            return AWS_CONSOLE_BASE_URL + 'ecs/home?region=' \
                + quote(aws_region) + '#/clusters/' \
                + quote(cluster_name) + '/tasks/' \
                + quote(task_id) + '/details'

    
class AwsEcsServiceDeploymentCircuitBreaker(PydanticSettingsModel):
    enable: bool = False
    rollback: bool = False


class AwsEcsServiceDeploymentAlarms(Boto3SerializableSettings):
    alarm_names: list[str] = None
    rollback: bool = False
    enable: bool = True


class AwsEcsServiceDeploymentLifecycleHook(AwsSubSettingsWithRole):
    hook_target_arn: str | None = None
    lifecycle_stages: list[LifecycleStage] | None = None
    hook_details: Any | None = None

class AwsEcsServiceDeploymentLinearConfiguration(Boto3SerializableSettings):
    step_percent: float | None = None
    step_bake_time_in_minutes: int | None = None

class AwsEcsServiceDeploymentCanaryConfiguration(Boto3SerializableSettings):
    canary_percent: float | None = None
    canary_bake_time_in_minutes: int | None = None

class AwsEcsServiceDeploymentConfiguration(Boto3SerializableSettings):
    maximum_percent: int | None = None
    minimum_healthy_percent: int | None = None
    deployment_circuit_breaker: AwsEcsServiceDeploymentCircuitBreaker | None = None
    alarms: AwsEcsServiceDeploymentAlarms | None = None
    strategy: DeploymentConfigurationStrategy | None = None
    bake_time_in_minutes: int | None = None
    lifecycle_hooks: list[AwsEcsServiceDeploymentLifecycleHook] | None = None
    linear_configuration: AwsEcsServiceDeploymentLinearConfiguration | None = None
    canary_configuration: AwsEcsServiceDeploymentCanaryConfiguration | None = None

    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:    
        for hook in (self.lifecycle_hooks or []):
            hook.update_derived_attrs(aws_settings=aws_settings)


class AwsApplicationLoadBalancerAdvancedConfiguration(AwsSubSettingsWithRole):
    alternate_target_group_arn: str | None = None
    production_listener_rule: str | None = None
    test_listener_rule: str | None = None

    @override
    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        super().update_derived_attrs(aws_settings=aws_settings)

        self.alternate_target_group_infrastructure_website_url = make_aws_console_target_group_url(
                self.alternate_target_group_arn)


class AwsApplicationLoadBalancer(Boto3SerializableSettings):
    target_group_arn: str | None = None
    target_group_infrastructure_website_url: str | None = \
        Field(default=None, exclude_if=EXCLUDE_IF_NONE)
    load_balancer_name: str | None = None
    container_name: str | None = None
    container_port: int | None = None
    advanced_configuration: AwsApplicationLoadBalancerAdvancedConfiguration | None = None

    def to_boto3_dict(self, main_container_name: str | None) -> dict[str, Any]:
        result = super().to_boto3_dict()

        if main_container_name and (self.container_name is None):
            result['containerName'] = main_container_name

        return result

    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        self.target_group_infrastructure_website_url = make_aws_console_target_group_url(self.target_group_arn)
        
        if self.advanced_configuration:
            self.advanced_configuration.update_derived_attrs(aws_settings=aws_settings)

class ServiceRegistry(Boto3SerializableSettings):
    registry_arn: str | None = None
    port: int | None = None
    container_name: str | None = None
    container_port: int | None = None


# Service Connect Configuration Models

class AwsServiceConnectTestTrafficRuleHeaderValue(Boto3SerializableSettings):
    exact: str | None = None

class AwsServiceConnectTestTrafficRuleHeader(Boto3SerializableSettings):
    name: str | None = None
    value: AwsServiceConnectTestTrafficRuleHeaderValue | None = None


class AwsServiceConnectTestTrafficRules(Boto3SerializableSettings):
    header: AwsServiceConnectTestTrafficRuleHeader | None = None

class AwsServiceConnectClientAlias(Boto3SerializableSettings):
    port: int | None = None
    dns_name: str | None = None
    test_traffic_rules: AwsServiceConnectTestTrafficRules | None = None

class AwsServiceConnectTimeout(Boto3SerializableSettings):
    idle_timeout_seconds: int | None = None
    per_request_timeout_seconds: int | None = None


class AwsServiceConnectIssuedCertificateAuthority(Boto3SerializableSettings):
    aws_pca_authority_arn: str | None = None


class AwsServiceConnectTls(AwsSubSettingsWithRole):
    issued_certificate_authority: AwsServiceConnectIssuedCertificateAuthority | None = None
    kms_key: str | None = None

class AwsServiceConnectService(Boto3SerializableSettings):
    port_name: str | None = None
    discovery_name: str | None = None
    client_aliases: list[AwsServiceConnectClientAlias] | None = None
    ingress_port_override: int | None = None
    timeout: AwsServiceConnectTimeout | None = None
    tls: AwsServiceConnectTls | None = None

    @override
    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        if self.tls:
            self.tls.update_derived_attrs(aws_settings=aws_settings)


class AwsServiceConnectLogConfigurationSecretOption(Boto3SerializableSettings):
    name: str | None = None
    value_from: str | None = None


class AwsServiceConnectLogConfiguration(Boto3SerializableSettings):
    log_driver: ServiceConnectLogDriver | None = None
    options: dict[str, str] | None = None
    secret_options: list[AwsServiceConnectLogConfigurationSecretOption] | None = None


class AwsServiceConnectAccessLogConfiguration(Boto3SerializableSettings):
    format: AccessLogFormat = DEFAULT_ACCESS_LOG_FORMAT
    include_query_parameters: AccessLogIncludeQueryParameters | None = None


class AwsServiceConnectConfiguration(Boto3SerializableSettings):
    enabled: bool | None = None
    namespace: str | None = None
    services: list[AwsServiceConnectService] | None = None
    log_configuration: AwsServiceConnectLogConfiguration | None = None
    access_log_configuration: AwsServiceConnectAccessLogConfiguration | None = None

    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        for service in (self.services or []):
            service.update_derived_attrs(aws_settings=aws_settings)


# Volume Configuration Models
class AwsVolumeTagSpecification(Boto3SerializableSettings):
    resource_type: str | None = None
    tags: list[AwsTagKeyValuePair] | None = None
    propagate_tags: VolumeTagPropagation | None = None


class AwsManagedEBSVolume(AwsSubSettingsWithRole):
    encrypted: bool | None = None
    kms_key_id: str | None = None
    kms_key_infrastructure_website_url: str | None = \
            Field(default=None, exclude_if=EXCLUDE_IF_NONE)
    volume_type: str | None = None
    size_in_gib: int | None = Field(None, alias='sizeInGiB')
    snapshot_id: str | None = None
    volume_initialization_rate: int | None = None
    iops: int | None = None
    throughput: int | None = None
    tag_specifications: list[AwsVolumeTagSpecification] | None = None
    filesystem_type: FilesystemType | None = None

    @override
    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        super().update_derived_attrs(aws_settings=aws_settings)
        
        self.kms_key_infrastructure_website_url = make_aws_console_kms_key_url(self.kms_key_id)

class AwsVolumeConfiguration(Boto3SerializableSettings):
    name: str
    managed_ebs_volume: AwsManagedEBSVolume | None = None

    @override
    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        if self.managed_ebs_volume:
            self.managed_ebs_volume.update_derived_attrs(aws_settings=aws_settings)


class AwsVpcLatticeConfiguration(AwsSubSettingsWithRole):
    target_group_arn: str | None = None
    target_group_infrastructure_website_url: str | None = \
            Field(default=None, exclude_if=EXCLUDE_IF_NONE)
    port_name: str | None = None

    @override
    def update_derived_attrs(self, aws_settings: AwsSettings | None) -> None:
        super().update_derived_attrs(aws_settings=aws_settings)
                
        self.target_group_infrastructure_website_url = make_aws_console_target_group_url(
                self.target_group_arn)

@dataclass
class AwsEcsServiceResponseFragment:
    service_dict: dict[str, Any]
    last_status: str
    service_arn: str
    service_name: str
    next_service_name_suffix: int | None = None
    tags: list[dict[str, str]] | None = None

    @staticmethod
    def from_boto_service_response_fragment(service_dict: dict[str, Any]) -> 'AwsEcsServiceResponseFragment':
        sd = service_dict
        service_name = sd['serviceName']
        service_arn = sd['serviceArn']
        last_status = sd['status'].upper()
        tags = sd.get('tags', [])
        
        logger.info(f"Last status of service '{service_name}' with ARN '{service_arn}' is {last_status}")

        index: int | None = None

        if last_status in ('DRAINING', 'ACTIVE', 'INACTIVE'):
            m = AwsEcsExecutionMethod.SERVICE_NAME_REGEX.match(service_name)

            if m:
                index_str = m.group(3)
                if index_str:
                    index = int(index_str)
                    if last_status != 'INACTIVE':
                        index += 1
            else:
                logger.warning(f"Can't match service name '{service_name}', will use 0 as suffix")
        else:
            logger.warning(f"Unexpected service status {last_status}")

        return AwsEcsServiceResponseFragment(
            service_dict = sd,
            last_status = last_status,
            service_arn = service_arn,
            service_name = service_name,
            next_service_name_suffix=index,
            tags=tags,
        )

@dataclass
class AwsEcsServiceTeardownResult:
    service_info: AwsEcsServiceResponseFragment | None = None

class AwsEcsServiceSettings(Boto3SerializableSettings):
    deployment_configuration: AwsEcsServiceDeploymentConfiguration | None = None
    scheduling_strategy: SchedulingStrategy | None = None
    force_new_deployment: bool | None = None
    availability_zone_rebalancing: AvailabilityZoneRebalancing | None = None
    health_check_grace_period_seconds: int | None = None
    load_balancers: list[AwsApplicationLoadBalancer] | None = None
    service_registries: list[ServiceRegistry] | None = None    
    service_connect_configuration: AwsServiceConnectConfiguration | None = None
    volume_configurations: list[AwsVolumeConfiguration] | None = None
    vpc_lattice_configurations: list[AwsVpcLatticeConfiguration] | None = None        
    resource_management_type: ResourceManagementType | None = None
    tags: list[AwsTagKeyValuePair] | None = None
    
    service_arn: str | None = None
    infrastructure_website_url: str | None = Field(default=None, exclude_if=EXCLUDE_IF_NONE)

    @override
    def update_derived_attrs(self, aws_ecs_settings: AwsEcsExecutionMethodSettings,
            aws_settings: AwsSettings | None):
        cluster_name = extract_ecs_cluster_name(aws_ecs_settings.cluster_arn)

        if cluster_name and self.service_arn:
            self.infrastructure_website_url = make_aws_console_ecs_service_url(
                ecs_service_arn=self.service_arn,
                cluster_name=cluster_name)
        else:
            self.infrastructure_website_url = None

        if self.deployment_configuration:
            self.deployment_configuration.update_derived_attrs(aws_settings=aws_settings)

        
        for lb in (self.load_balancers or []):
            lb.update_derived_attrs(aws_settings=aws_settings)

        if self.service_connect_configuration:
            self.service_connect_configuration.update_derived_attrs(aws_settings=aws_settings)

        for volume_config in (self.volume_configurations or []):
            volume_config.update_derived_attrs(aws_settings=aws_settings)

        for vpc_lattice_config in (self.vpc_lattice_configurations or []):
            vpc_lattice_config.update_derived_attrs(aws_settings=aws_settings)

    @override
    def get_boto3_excluded_field_names(self) -> set[str]:
        return set(['service_arn'])

    @staticmethod
    def from_boto_service_response_fragment(service_dict: dict[str, Any]) -> AwsEcsServiceSettings:
        return AwsEcsServiceSettings.model_validate(service_dict)
    
class AwsEcsExecutionMethod(AwsBaseExecutionMethod):
    NAME = 'AWS ECS'
    
    DEFAULT_LAUNCH_TYPE = LAUNCH_TYPE_FARGATE
    DEFAULT_CPU_UNITS = 256
    DEFAULT_MEMORY_MB = 512

    SERVICE_NAME_REGEX = re.compile(r"^(.+?)(_(\d+))?$")

    DEFAULT_LOAD_BALANCER_HEALTH_CHECK_GRACE_PERIOD_SECONDS = 300

    SERVICE_PROPAGATE_TAGS_TASK_DEFINITION = 'TASK_DEFINITION'
    SERVICE_PROPAGATE_TAGS_SERVICE = 'SERVICE'

    SERVICE_PROPAGATE_TAGS_CHOICES = [
        SERVICE_PROPAGATE_TAGS_TASK_DEFINITION,
        SERVICE_PROPAGATE_TAGS_SERVICE,
    ]

    CAPABILITIES_WITHOUT_SCHEDULING = frozenset([
        ExecutionMethod.ExecutionCapability.MANUAL_START,
        ExecutionMethod.ExecutionCapability.SETUP_SERVICE
    ])

    MAX_TAG_COUNT = 50

    EXECUTION_METHOD_ATTRIBUTES_REQUIRING_SCHEDULING_UPDATE = [
        'task_definition_arn',
        'launch_type',
        'cluster_arn',
        'platform_version',
        'execution_role_arn',
    ]

    NETWORK_ATTRIBUTES_REQUIRING_SCHEDULING_UPDATE = [
        'subnets',
        'security_groups',
        'assign_public_ip'
    ]


    def __init__(self,
            task: Task | None = None,
            task_execution: TaskExecution | None = None,
            aws_settings: dict[str, Any] | None = None,
            aws_ecs_settings: dict[str, Any] | None = None) -> None:
        super().__init__(self.NAME, task=task, task_execution=task_execution,
                aws_settings=aws_settings)

        task = self.task

        if aws_ecs_settings is None:
            aws_ecs_settings = self.merge_aws_ecs_settings_dict(task=task,
                task_execution=task_execution)

        logger.debug(f"{aws_ecs_settings=}")

        if task_execution:
            self.settings = cast(AwsEcsExecutionMethodSettings,
                    AwsEcsExecutionMethodInfo.model_validate(aws_ecs_settings))
        else:
            self.settings = AwsEcsExecutionMethodSettings.model_validate(aws_ecs_settings)

        self.service_settings: AwsEcsServiceSettings | None = None
        self.scheduling_settings: AwsCloudwatchSchedulingSettings | None = None

        if task and (task_execution is None):
            if task.service_settings is not None:
                self.service_settings = AwsEcsServiceSettings.model_validate(task.service_settings)

            if task.scheduling_settings is not None:
                self.scheduling_settings = AwsCloudwatchSchedulingSettings.model_validate(
                    task.scheduling_settings)


    @staticmethod
    def merge_aws_ecs_settings_dict(task: Task | None,
            task_execution: TaskExecution | None) -> dict[str, Any]:

        settings_to_merge: list[dict[str, Any]] = [ {} ]

        if task:
            settings_to_merge = []

            if task.run_environment:
                settings_to_merge.append(task.run_environment.default_aws_ecs_configuration or {})

            settings_to_merge.append(task.execution_method_capability_details or {})

        if task_execution and task_execution.execution_method_details:
            settings_to_merge.append(task_execution.execution_method_details)

        return deepmerge(*settings_to_merge)

    @override
    def capabilities(self) -> FrozenSet[ExecutionMethod.ExecutionCapability]:
        task = self.task

        if task and task.passive:
            return frozenset()

        aws_settings = self.aws_settings

        if not aws_settings.can_manage_infrastructure():
            logger.debug("Can't control ECS")
            return frozenset()

        network = self.aws_settings.network

        subnets: list[str] | None = None

        if network:
            subnets = network.subnets

        if not subnets:
            return frozenset()

        return ExecutionMethod.ALL_CAPABILITIES


    def should_update_or_force_recreate_scheduled_execution(self,
            old_execution_method: ExecutionMethod | None=None) \
            -> tuple[bool, bool]:
        should = super().should_maybe_update_scheduled_execution(
                old_execution_method=old_execution_method)

        if should is not None:
            return (should, True)

        if old_execution_method is None:
            return (True, True)

        network = self.aws_settings.network

        if network is None:
            logger.warning("should_update_scheduled_execution(): No network settings found, returning true so an exception happens later")
            return (True, True)

        old_task = old_execution_method.task

        if (not old_task) or (old_task.execution_method_capability_details is None) or \
            (old_task.execution_method_type != AwsEcsExecutionMethod.NAME) or \
            (old_task.infrastructure_settings is None) or \
            (old_task.infrastructure_type != INFRASTRUCTURE_TYPE_AWS):
            return (True, True)

        old_aws_ecs_execution_method = cast(AwsEcsExecutionMethod, old_execution_method)
        old_settings = old_aws_ecs_execution_method.settings

        for attr in self.EXECUTION_METHOD_ATTRIBUTES_REQUIRING_SCHEDULING_UPDATE:
            old_value = getattr(old_settings, attr)
            new_value = getattr(self.settings, attr)

            if new_value != old_value:
                logger.info(f"{attr} changed from {old_value} to {new_value}, adjusting schedule")
                return (True, True)

        old_aws_settings = old_aws_ecs_execution_method.aws_settings
        old_network = old_aws_settings.network

        if old_network is None:
            logger.info("should_update_scheduled_execution() Task previously had no network settings, returning true")
            return (True, True)

        for attr in self.NETWORK_ATTRIBUTES_REQUIRING_SCHEDULING_UPDATE:
            old_value = getattr(old_network, attr)
            new_value = getattr(network, attr)

            if new_value != old_value:
                logger.info(f"{attr} changed from {old_value} to {new_value}, adjusting schedule")
                return (True, True)

        return (False, False)

    @override
    def setup_scheduled_execution(self, old_execution_method: ExecutionMethod | None=None,
            force_creation: bool=False, teardown_result: Any | None=None) -> None:
        task = self.task

        if not task:
            raise RuntimeError("No Task found")

        if not task.has_active_managed_scheduled_execution(current=False):
            raise RuntimeError("setup_scheduled_execution() called but the Task is not going to be actively scheduled")

        if task.scheduling_provider_type and \
                (task.scheduling_provider_type != SCHEDULING_TYPE_AWS_CLOUDWATCH):
            raise RuntimeError(f"setup_scheduled_execution() called but {task.scheduling_provider_type=} is unsupported")

        if not task.schedule.startswith('cron') and not task.schedule.startswith('rate'):
            raise APIException(detail=f"Schedule '{task.schedule}' is invalid")

        aws_scheduled_execution_rule_name = f"CR_{task.uuid}"

        client = self.aws_settings.make_events_client()

        ss = self.scheduling_settings or AwsCloudwatchSchedulingSettings()

        kwargs = {
            'Name': aws_scheduled_execution_rule_name,
            'ScheduleExpression': task.schedule,
            #EventPattern='true',
            'State': 'ENABLED',
            'Description': f"Scheduled execution of Task '{task.name}' ({task.uuid})"
        }

        tags = self.compute_tags(for_scheduled_task=True)

        if tags:
            kwargs['Tags'] = [ 
                { 'Key': pair.key, 'Value': pair.value } \
                    for pair in AwsTagKeyValuePair.dict_to_pair_list(tags)
            ]

        execution_role_arn = self.settings.execution_role_arn
        logger.info(f"Using execution role arn = '{execution_role_arn}'")

        if execution_role_arn:
            kwargs['RoleArn'] = execution_role_arn

        if ss.event_bus_name:
            kwargs['EventBusName'] = ss.event_bus_name

        # Need this permission: https://github.com/Miserlou/Zappa/issues/381
        response = client.put_rule(**kwargs)

        aws_scheduled_event_rule_arn = response['RuleArn']
        logger.info(f"got rule ARN = {aws_scheduled_event_rule_arn}")

        ss.execution_rule_name = aws_scheduled_execution_rule_name
        ss.event_rule_arn = aws_scheduled_event_rule_arn

        self.scheduling_settings = ss

        task.is_scheduling_managed = True
        task.scheduling_provider_type = SCHEDULING_TYPE_AWS_CLOUDWATCH
        task.scheduling_settings = ss.model_dump()

        client.enable_rule(Name=aws_scheduled_execution_rule_name)

        aws_event_target_rule_name = f"CR_{task.uuid}"
        aws_event_target_id = f"CR_{task.uuid}"
        platform_version = self.settings.platform_version or AWS_ECS_PLATFORM_VERSION_LATEST

        task_network = self.aws_settings.network

        if not task_network:
            raise APIException("Cannot schedule Task: no network settings found")

        assign_public_ip = self.assign_public_ip_str()


        ecs_parameters ={
            'TaskDefinitionArn': self.settings.task_definition_arn,
            'TaskCount': task.scheduled_instance_count or 1,            
            # Only for tasks that use awsvpc networking
            'NetworkConfiguration': {
                'awsvpcConfiguration': {
                    'Subnets': task_network.subnets,
                    'SecurityGroups': task_network.security_groups,
                    'AssignPublicIp': assign_public_ip
                }
            },
            'PlatformVersion': platform_version,
        }

        task_group = self.settings.task_group

        if task_group:
            ecs_parameters['Group'] = task_group

        if self.settings.capacity_provider_strategy:
            ecs_parameters['CapacityProviderStrategy'] = self.settings.boto3_capacity_provider_strategy_value()
        else:            
            ecs_parameters['LaunchType'] = self.settings.launch_type or self.DEFAULT_LAUNCH_TYPE

        if self.settings.enable_execute_command is not None:
            ecs_parameters['EnableExecuteCommand'] = self.settings.enable_execute_command

        if self.settings.propagate_tags:
            ecs_parameters['PropagateTags'] = self.settings.propagate_tags

        if self.settings.enable_ecs_managed_tags is not None:
            ecs_parameters['EnableECSManagedTags'] = self.settings.enable_ecs_managed_tags

        response = client.put_targets(
            Rule=aws_event_target_rule_name,
            Targets=[
                {
                    'Id': aws_event_target_id,
                    'Arn': self.settings.cluster_arn,
                    'RoleArn': self.aws_settings.events_role_arn,
                    'EcsParameters': ecs_parameters,
                },
            ]
        )
        handle_aws_multiple_failure_response(response)

        ss.event_target_rule_name = aws_event_target_rule_name
        ss.event_target_id = aws_event_target_id

        task.scheduling_settings = ss.model_dump()

    @override
    def teardown_scheduled_execution(self) -> tuple[dict[str, Any] | None, Any | None]:
        task = self.task

        if not task:
            raise RuntimeError("No Task found")

        if task.is_scheduling_managed is False:
            return (None, None)

        if task.scheduling_provider_type and \
                (task.scheduling_provider_type != SCHEDULING_TYPE_AWS_CLOUDWATCH):
            raise RuntimeError(f"teardown_scheduled_execution() called but {task.scheduling_provider_type=} is unsupported")

        ss = self.scheduling_settings

        if not ss:
            if task.is_scheduling_managed:
                task.is_scheduling_managed = None
                task.scheduling_provider_type = ''
            return (None, None)

        client: Any | None = None

        if ss.event_target_rule_name and ss.event_target_id:
            client = self.aws_settings.make_events_client()

            try:
                kwargs = {
                    'Rule': ss.event_target_rule_name,
                    'Ids': [
                        ss.event_target_id
                    ],
                    'Force': False
                }

                if ss.event_bus_name:
                    kwargs['EventBusName'] = ss.event_bus_name

                response = client.remove_targets(**kwargs)
                handle_aws_multiple_failure_response(response)
            except ClientError as client_error:
                error_code = client_error.response['Error']['Code']
                # Happens if the schedule rule is removed manually
                if error_code == 'ResourceNotFoundException':
                    logger.warning(f"teardown_scheduled_execution(): Can't remove target {ss.event_target_rule_name} because resource not found, exception = {client_error}")
                else:
                    logger.exception(f"teardown_scheduled_execution(): Can't remove target {ss.event_target_rule_name} due to unhandled error {error_code}")
                    raise client_error

            ss.event_target_rule_name = None
            ss.event_target_id = None
            self.scheduling_settings = ss
            task.scheduling_settings = ss.model_dump()

        if ss.execution_rule_name:
            client = client or self.aws_settings.make_events_client()

            try:
                kwargs = {
                    'Name': ss.execution_rule_name,
                    'Force': True
                }

                if ss.event_bus_name:
                    kwargs['EventBusName'] = ss.event_bus_name

                client.delete_rule(**kwargs)
            except ClientError as client_error:
                error_code = client_error.response['Error']['Code']
                # Happens if the schedule rule is removed manually
                if error_code == 'ResourceNotFoundException':
                    logger.warning(
                        f"teardown_scheduled_execution(): Can't delete rule {ss.execution_rule_name} because resource not found, exception = {client_error}")
                else:
                    logger.exception(
                        f"teardown_scheduled_execution(): Can't delete rule {ss.execution_rule_name} due to unhandled error {error_code}")
                    raise client_error

            ss.execution_rule_name = None
            ss.event_rule_arn = None

            self.scheduling_settings = ss
            task.scheduling_settings = ss.model_dump()
            task.is_scheduling_managed = None

        return (task.scheduling_settings, None)

    def should_update_or_force_recreate_service(self, old_execution_method: ExecutionMethod | None=None) -> tuple[bool, bool]:
        task = self.task

        if not task:
            raise RuntimeError("No Task found")

        will_be_managed_service = task.is_active_managed_service(current=False)

        old_task: Task | None = None
        old_aws_ecs_execution_method: AwsEcsExecutionMethod | None = None

        if old_execution_method:
            old_task = old_execution_method.task

            if isinstance(old_execution_method, AwsEcsExecutionMethod):
                old_aws_ecs_execution_method = cast(AwsEcsExecutionMethod,
                        old_execution_method)

        was_managed_ecs_service = bool(old_task and old_aws_ecs_execution_method and \
                old_task.is_active_managed_service() and \
                (old_task.service_provider_type == SERVICE_PROVIDER_AWS_ECS) and \
                old_aws_ecs_execution_method.service_settings and \
                old_aws_ecs_execution_method.service_settings.service_arn)

        logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {was_managed_ecs_service=}, {will_be_managed_service=}")

        if not will_be_managed_service:
            return (was_managed_ecs_service, False)

        if task.service_provider_type != SERVICE_PROVIDER_AWS_ECS:
            raise APIException(f"Unsupported service provider '{task.service_provider_type}'")

        ss = self.service_settings

        logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} service_settings = {ss}")

        if not was_managed_ecs_service:
            logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} was_managed_ecs_service=false, forcing recreate")
            return (True, True)
        
        if (not old_task) or (old_task.service_settings is None) or \
                (not old_aws_ecs_execution_method):
            logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} missing old_aws_ecs_execution_method, forcing recreate")
            return (True, True)
        
        try:
            old_settings = old_aws_ecs_execution_method.settings

            logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {old_settings=}")

            old_launch_type = old_settings.launch_type
            new_launch_type = self.settings.launch_type

            if old_launch_type and old_settings.capacity_provider_strategy:
                old_launch_type = None

            if new_launch_type and self.settings.capacity_provider_strategy:
                new_launch_type = None

            if (old_launch_type != new_launch_type) or \
                  (old_settings.cluster_arn != self.settings.cluster_arn):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} launch type or cluster differs, forcing recreate")
                return (True, True)

            old_ss = old_aws_ecs_execution_method.service_settings

            if (not old_ss) or (not old_ss.service_arn):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} old service settings = {old_ss} missing service_arn, forcing recreate")
                return (True, True)

            if ss and ss.service_arn and (ss.service_arn != old_ss.service_arn):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {ss.service_arn=} != {old_ss.service_arn=}, forcing recreate")
                return (True, True)

            if ss and ss.resource_management_type and (ss.resource_management_type != old_ss.resource_management_type):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {ss.resource_management_type=} != {old_ss.resource_management_type=}, forcing recreate")
                return (True, True)

            old_aws_settings = old_aws_ecs_execution_method.aws_settings

            if not old_aws_settings:
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} missing old AWS settings, update required but not recreate")
                return (True, False)

            old_network = old_aws_settings.network
            if not old_network:
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {old_aws_settings=} missing network, update required but not recreate")
                return (True, False)

            # TODO: network cannot change for non-ECS deployment controllers
            # if (not old_network) or (not old_network.subnets):
            #     return (True, True)

            # TODO: load balancers cannot change for non-ECS deployment controllers
            # old_lbs = old_ss.load_balancer_settings
            # lbs = ss.load_balancer_settings

            # if lbs:
            #     lb_list = lbs.load_balancers or []

            #     if not old_lbs:
            #         return (True, bool(lb_list))

            #     old_lb_list = old_lbs.load_balancers or []
            #     old_target_group_arn_to_lb: dict[str, AwsApplicationLoadBalancer] = {}
            #     for old_lb in old_lb_list:
            #         if old_lb.target_group_arn:
            #             old_target_group_arn_to_lb[old_lb.target_group_arn] = old_lb

            #     for lb in lb_list:
            #         if not lb.target_group_arn:
            #             continue

            #         old_lb_2 = old_target_group_arn_to_lb.pop(lb.target_group_arn, None)

            #         if old_lb_2:
            #             if (old_lb_2.container_name != lb.container_name) or \
            #                     (old_lb_2.container_port != lb.container_port):
            #                 logger.info(f"Found different details for target group ARN: '{lb.target_group_arn}': {lb}")
            #                 return (True, True)
            #         else:
            #             logger.info(f"Found new target group ARN: '{lb.target_group_arn}', must recreate service")
            #             return (True, True)

            #     if bool(old_target_group_arn_to_lb) or \
            #             (old_lbs.health_check_grace_period_seconds != lbs.health_check_grace_period_seconds):
            #         return (True, True)
            # elif old_lbs:
            #     return (True, True)            

            # recreate is False from here down
        
            if old_task.service_instance_count != task.service_instance_count:
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} Task settings changed, update required, but not recreate (1)")
                return (True, False)

            if (old_settings.task_definition_arn != self.settings.task_definition_arn) or \
                    (old_settings.platform_version != self.settings.platform_version) or \
                    (old_settings.capacity_provider_strategy != self.settings.capacity_provider_strategy) or \
                    (old_settings.enable_execute_command != self.settings.enable_execute_command) or \
                    (old_settings.propagate_tags != self.settings.propagate_tags) or \
                    (old_settings.enable_ecs_managed_tags != self.settings.enable_ecs_managed_tags):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} ECS settings changed, update required, but not recreate (3)")
                return (True, False)

            if (old_aws_ecs_execution_method.compute_tags(for_service=True) != \
                self.compute_tags(for_service=True)):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} tags changed, update required but not recreate")
                return (True, False)

            network = self.aws_settings.network

            if (not network) or (not network.subnets):
                raise APIException("Missing network settings for service")

            if (not old_network.subnets) or (set(old_network.subnets) != set(network.subnets)):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} subnets have changed from {old_network.subnets} to {network.subnets}, update required but not recreate")
                return (True, False)

            if set(network.security_groups or []) != set(old_network.security_groups or []):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} security groups have changed from {old_network.security_groups} to {network.security_groups}, update required but not recreate")
                return (True, False)

            if (old_ss.deployment_configuration != ss.deployment_configuration) or \
                    (old_ss.scheduling_strategy != ss.scheduling_strategy) or \
                    (old_ss.force_new_deployment != ss.force_new_deployment) or \
                    (old_ss.availability_zone_rebalancing != ss.availability_zone_rebalancing) or \
                    (old_ss.health_check_grace_period_seconds != ss.health_check_grace_period_seconds) or \
                    (old_ss.load_balancers != ss.load_balancers) or \
                    (old_ss.service_registries != ss.service_registries) or \
                    (old_ss.volume_configurations != ss.volume_configurations) or \
                    (old_ss.vpc_lattice_configurations != ss.vpc_lattice_configurations):
                logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} {old_ss=}, {ss=}, requires update but no recreate (2)")
                return (True, False)
        except Exception:
            logger.warning(f"Can't parse old Task service settings: {task.uuid=} {old_ss}", exc_info=True)
            return (True, True)

        logger.info(f"should_update_or_force_recreate_service(): {task.uuid=} no update or recreate required")

        return (False, False)

    @override
    def setup_service(self, old_execution_method: ExecutionMethod | None=None,
            force_creation: bool=False, teardown_result: Any | None=None) -> None:
        task = self.task

        if not task:
            raise RuntimeError("No Task found")

        if self.service_settings is None:
            self.service_settings = AwsEcsServiceSettings()

        ss = self.service_settings

        logger.info(f"setup_service() for Task {task.name}, {force_creation=}, {teardown_result=} ...")

        old_aws_ecs_execution_method: AwsEcsExecutionMethod | None = None
        old_ecs_client: Any | None = None
        existing_service_info: AwsEcsServiceResponseFragment | None = None
        aws_ecs_service_teardown_result: AwsEcsServiceTeardownResult | None = None

        if isinstance(old_execution_method, AwsEcsExecutionMethod):
            old_aws_ecs_execution_method = cast(AwsEcsExecutionMethod, old_execution_method)

            if teardown_result:
                aws_ecs_service_teardown_result = cast(AwsEcsServiceTeardownResult, teardown_result)
                existing_service_info = aws_ecs_service_teardown_result.service_info
                logger.info(f"setup_service(): {task.uuid} got {existing_service_info=} from teardown result")

        if (existing_service_info is None) and old_aws_ecs_execution_method:
            old_service_settings = old_aws_ecs_execution_method.service_settings
            old_service_arn: str | None = None

            if old_service_settings:
                old_service_arn = old_service_settings.service_arn
                logger.info(f"setup_service(): {task.uuid} found {old_service_arn=}")
            else:
                logger.info(f"setup_service(): {task.uuid} old_service_arn not found")

            try:
                old_ecs_client = old_aws_ecs_execution_method.make_ecs_client()
                existing_service_info = old_aws_ecs_execution_method.find_aws_ecs_service(
                        ecs_client=old_ecs_client, service_arn_or_name=old_service_arn)
            except Exception:
                logger.warning("Cannot find existing ECS service with old execution method")

        ecs_client: Any | None = None

        if not existing_service_info:
            ecs_client = self.make_ecs_client()
            existing_service_info = self.find_aws_ecs_service(ecs_client=ecs_client,
                    service_arn_or_name=ss.service_arn)

        # When creating a service that specifies multiple target groups, the Amazon ECS service-linked role must be created. The role is created by omitting the role parameter in API requests, or the Role property in AWS CloudFormation. For more information, see Service-Linked Role for Amazon ECS.
        # role = task.aws_ecs_default_task_role or task.aws_ecs_default_execution_role or \
        #    run_env.aws_ecs_default_task_role or run_env.aws_ecs_default_execution_role

        service_name: str | None = None
        if existing_service_info:
            last_status = existing_service_info.last_status
            service_name = existing_service_info.service_name

            logger.info(f"setup_service() for Task {task.uuid} found existing service {service_name}")
            if force_creation and (last_status == 'ACTIVE'):
                if old_aws_ecs_execution_method:
                    logger.info(f"setup_service(): deleting ACTIVE service {service_name} ...")
                    old_ecs_client = old_ecs_client or old_aws_ecs_execution_method.make_ecs_client()
                    existing_service_info = old_aws_ecs_execution_method.delete_service(
                            service_name=service_name, ecs_client=old_ecs_client)
                else:
                    logger.warning(f"setup_service(): {task.uuid} service {service_name} existed before Task was saved as an AWS ECS Task?")
                    # TODO: how to recover?
            else:
                logger.info(f"setup_service() {task.uuid} not deleting existing service {service_name}")

        if (existing_service_info is None) or (last_status == 'INACTIVE'):
            logger.info(f"Clearing service_arn for inactive or missing service {service_name or 'N/A'}")

            # TODO: set generic service_updated_at column
            task.aws_ecs_service_updated_at = timezone.now()

            ss.service_arn = None
            task.service_settings = ss.model_dump()

            # Can't save if this is part of a creation request
            if task.pk:
                task.save_without_sync()

        ecs_client = ecs_client or self.make_ecs_client()

        if (not force_creation) and existing_service_info and \
                (existing_service_info.last_status == 'ACTIVE'):
            logger.info(f"setup_service() for Task {task.name} updating service ...")

            args = self.make_common_service_args(include_launch_type=False)
            args['service'] = service_name
            args['forceNewDeployment'] = ss.force_new_deployment or False

            response = ecs_client.update_service(**args)

            updated_service_info = AwsEcsServiceResponseFragment.from_boto_service_response_fragment(
                    service_dict=response['service'])
            current_tag_list = updated_service_info.tags or []
            current_tags = { pair.key: pair.value for pair in current_tag_list }

            new_tag_pair_list = ss.tags or []
            tags_to_add: list[dict[str, str]] = []
            tags_to_remove: list[str] = []
            for pair in new_tag_pair_list:
                k = pair.key
                v = pair.value

                if (k not in current_tags) or (current_tags.get(k) != v):
                    tags_to_add.append({ 'key': k, 'value': v })

            new_tags = AwsTagKeyValuePair.pair_list_to_dict(new_tag_pair_list)
            tags_to_remove: list[str] = []
            
            for k, in current_tags.keys():
                if k not in new_tags:
                    tags_to_remove.append(k)

            logger.info(f"setup_service() for Task {task.name} updating tags from {current_tags} to {new_tags} ...")

            if tags_to_remove:
                logger.info(f"setup_service() for Task {task.name} removing tags {tags_to_remove} ...")
                ecs_client.untag_resource(
                    resourceArn=ss.service_arn,
                    tagKeys=tags_to_remove
                )

            if tags_to_add:
                logger.info(f"setup_service() for Task {task.name} adding tags {tags_to_add} ...")
                ecs_client.tag_resource(
                    resourceArn=ss.service_arn,
                    tags=tags_to_add
                )
        else:
            args = self.add_creation_args(self.make_common_service_args(
                    include_launch_type=True), for_service=True)

            new_service_name: str | None = None

            if service_name is None:
                new_service_name = self.make_aws_ecs_service_name()
            elif existing_service_info:
                new_service_name = self.make_aws_ecs_service_name(
                        index=existing_service_info.next_service_name_suffix or 0)

            logger.info(f"setup_service() for Task {task.name} creating service with {new_service_name=} ...")

            args['serviceName'] = new_service_name

            client_token = ''.join(random.choice(string.ascii_letters) for i in range(30))
            args['clientToken'] = client_token
            args['schedulingStrategy'] = ss.scheduling_strategy or DEFAULT_SCHEDULING_STRATEGY
            args['deploymentController'] = {
                # TODO: support EXTERNAL deployment controller for running on EKS or self-managed Kubernetes
                'type': 'ECS'
            }

            response = ecs_client.create_service(**args)

        service_info = AwsEcsServiceResponseFragment.from_boto_service_response_fragment(
                service_dict=response['service'])

        task.aws_ecs_service_updated_at = timezone.now()

        ss.service_arn = service_info.service_arn
        task.service_settings = ss.model_dump()

        logger.info(f"setup_service() for Task {task.name} got service ARN {ss.service_arn} ...")

    @override
    def teardown_service(self) -> tuple[dict[str, Any] | None, Any | None]:
        task = self.task

        if not task:
            raise RuntimeError("teardown_service(): No Task found")

        logger.info(f"Tearing down service for Task {task.name} ...")

        teardown_result = AwsEcsServiceTeardownResult()
        ssd: dict[str, Any] | None = None

        ecs_client = self.make_ecs_client()
        existing_service_info = self.find_aws_ecs_service(ecs_client=ecs_client)

        if existing_service_info and self.settings.cluster_arn:
            # TODO: Mark Task Executions as STOPPED so they are aborted the next
            # time they heartbeat

            service_name = existing_service_info.service_name
            service_info = self.delete_service(
                    service_name=service_name,
                    ecs_client=ecs_client)

            teardown_result.service_info = service_info

            if service_info.last_status == 'INACTIVE':
                logger.info(f'Service {service_name} was inactive, clearing service ARN')

                if self.service_settings:
                    self.service_settings.service_arn = None
                    ssd = self.service_settings.model_dump()
                    task.service_settings = ssd
            else:
                logger.info(f'Service {service_name} had status {service_info.last_status}, saving service ARN')

                # The service ARN is not modified so that the name can be
                # incremented next time the service is enabled.
                service_arn = service_info.service_arn

                if self.service_settings:
                    self.service_settings.service_arn = service_arn
                else:
                    self.service_settings = AwsEcsServiceSettings.from_boto_service_response_fragment(
                            service_dict=service_info.service_dict)

                ssd = self.service_settings.model_dump()
                task.service_settings = ssd

            task.aws_ecs_service_updated_at = timezone.now()
        else:
            logger.info(f"Tearing down service for Task {task.name} was a no-op since service was not found")

            if self.service_settings:
                self.service_settings.service_arn = None
                ssd = self.service_settings.model_dump()

        return (ssd, teardown_result)

    @override
    def manually_start(self) -> None:
        task_execution = self.task_execution

        if task_execution is None:
            raise APIException("No Task Execution found")

        task = self.task

        if task is None:
            raise APIException("No Task found")

        if task_execution.is_service is None:
            task_execution.is_service = task.is_service

        task_execution.heartbeat_interval_seconds = task_execution.heartbeat_interval_seconds or task.heartbeat_interval_seconds
        task_execution.task_max_concurrency = task_execution.task_max_concurrency or task.max_concurrency
        task_execution.max_conflicting_age_seconds = task_execution.max_conflicting_age_seconds or task.max_age_seconds

        if task_execution.process_max_retries is None:
            task_execution.process_max_retries = task.default_max_retries

        args = self.add_creation_args(self.make_common_args(include_launch_type=True))

        if self.settings.task_group:
            args['group'] = self.settings.task_group

        cpu_units = task_execution.allocated_cpu_units \
                or task.allocated_cpu_units or self.DEFAULT_CPU_UNITS
        memory_mb = task_execution.allocated_memory_mb \
                or task.allocated_memory_mb or self.DEFAULT_MEMORY_MB

        logger.info(f"manually_start() with args = {args}, " +
            f"{cpu_units=}, {memory_mb=}, " +
            f"{self.settings.execution_role_arn=}, {self.settings.task_role_arn=}")

        task_execution.allocated_cpu_units = cpu_units
        task_execution.allocated_memory_mb = memory_mb

        aws_ecs_settings = AwsEcsExecutionMethodInfo.model_validate(
            task_execution.execution_method_details or {})

        aws_ecs_settings.cluster_arn = self.settings.cluster_arn
        aws_ecs_settings.task_definition_arn = self.settings.task_definition_arn
        aws_ecs_settings.platform_version = self.settings.platform_version
        aws_ecs_settings.launch_type = self.settings.launch_type
        aws_ecs_settings.execution_role_arn = self.settings.execution_role_arn
        aws_ecs_settings.task_role_arn = self.settings.task_role_arn
        aws_ecs_settings.task_group = self.settings.task_group

        task_aws_ecs_settings = AwsEcsExecutionMethodInfo.model_validate(
            task.execution_method_capability_details or {})

        main_container_cpu_units = aws_ecs_settings.main_container_cpu_units
        computed_main_container_cpu_units: int | None = None

        if (main_container_cpu_units is None) and task.allocated_cpu_units and task_aws_ecs_settings.main_container_cpu_units:
            computed_main_container_cpu_units = (cpu_units - task.allocated_cpu_units) + task_aws_ecs_settings.main_container_cpu_units

            if (main_container_cpu_units is not None) and (main_container_cpu_units != computed_main_container_cpu_units):
                logger.warning(f"Overriding {main_container_cpu_units=} with {computed_main_container_cpu_units=}")

            main_container_cpu_units = computed_main_container_cpu_units

        main_container_memory_mb = aws_ecs_settings.main_container_memory_mb

        computed_main_container_memory_mb: int | None = None

        if (main_container_memory_mb is None) and task.allocated_memory_mb and task_aws_ecs_settings.main_container_memory_mb:
            computed_main_container_memory_mb = (memory_mb - task.allocated_memory_mb) + task_aws_ecs_settings.main_container_memory_mb

            if (main_container_memory_mb is not None) and (main_container_memory_mb != computed_main_container_memory_mb):
                logger.warning(f"Overriding {main_container_memory_mb=} with {computed_main_container_memory_mb=}")

            main_container_memory_mb = computed_main_container_memory_mb

        aws_ecs_settings.main_container_cpu_units = main_container_cpu_units
        aws_ecs_settings.main_container_memory_mb = main_container_memory_mb

        task_execution.execution_method_type = self.NAME
        task_execution.execution_method_details = aws_ecs_settings.model_dump()

        aws_settings = AwsSettings.model_validate(task_execution.infrastructure_settings or {})
        network = aws_settings.network

        if network is None:
            network = AwsNetworkSettings()
            aws_settings.network = network

        merged_network = self.aws_settings.network

        if merged_network is None:
            merged_network = AwsNetworkSettings()

        network.subnets = merged_network.subnets
        network.security_groups = merged_network.security_groups
        network.assign_public_ip = merged_network.assign_public_ip

        task_execution.infrastructure_type = INFRASTRUCTURE_TYPE_AWS
        task_execution.infrastructure_settings = aws_settings.model_dump()

        task_execution.save()
        task.latest_task_execution = task_execution
        task.save_without_sync()


        # Deployers used to use the task name as the main container name, but
        # that should have been saved. If somehow the setting is not present,
        # use the default main container name.
        main_container_name = self.settings.main_container_name or DEFAULT_MAIN_CONTAINER_NAME

        main_container_override: dict[str, Any] = {
            'name': main_container_name
        }

        if main_container_cpu_units:
            main_container_override['cpu'] = main_container_cpu_units

        if main_container_memory_mb:
            main_container_override['memory'] = main_container_memory_mb

#                    {
#                        'command': [
#                            'string',
#                        ],
#                        'memoryReservation': task_execution.allocated_memory_mb or task.allocated_memory_mb,
#                        'resourceRequirements': [
#                            {
#                                'value': 'string',
#                                'type': 'GPU'
#                            },
#                       ]

        container_overrides = [
            main_container_override
        ]

        main_container_is_monitor = True
        if self.settings.monitor_container_name and \
                (self.settings.monitor_container_name != self.settings.main_container_name):
            monitor_container_override = {
                'name': self.settings.monitor_container_name,
                'environment': make_flattened_environment(
                        env=task_execution.make_environment(include_app_vars=False))
            }
            container_overrides.append(monitor_container_override)
            main_container_is_monitor = False


        main_container_override['environment'] = make_flattened_environment(
                env=task_execution.make_environment(include_wrapper_vars=main_container_is_monitor))

        success = False
        try:
            ecs_client = self.aws_settings.make_boto3_client('ecs',
                    session_uuid=str(task_execution.uuid))

            overrides = {
                'containerOverrides': container_overrides,
                'executionRoleArn': self.settings.execution_role_arn,
            }

            if self.settings.task_role_arn:
                overrides['taskRoleArn'] = self.settings.task_role_arn

            args.update({
                'overrides': overrides,
                'count': 1,
                'startedBy': 'CloudReactor',
                # placementConstraints=[
                #     {
                #         'type': 'distinctInstance' | 'memberOf',
                #         'expression': 'string'
                #     },
                # ],
                # placementStrategy=[
                #     {
                #         'type': 'random' | 'spread' | 'binpack',
                #         'field': 'string'
                #     },
                # ],
            })

            if self.settings.enable_ecs_managed_tags is not None:
                args['enableECSManagedTags'] = self.settings.enable_ecs_managed_tags

            if self.settings.propagate_tags:
                args['propagateTags'] = self.settings.propagate_tags

            if self.settings.enable_execute_command is not None:
                args['enableExecuteCommand'] = self.settings.enable_execute_command

            if self.settings.task_group:
                args['group'] = self.settings.task_group

            rv = ecs_client.run_task(**args)

            logger.info(f"Got run_task() return value {rv}")

            # TODO: handle failures in rv['failures'][]

            task_arn = rv['tasks'][0]['taskArn']
            cast(AwsEcsExecutionMethodInfo, self.settings).task_arn = task_arn
            task_execution.execution_method_details['task_arn'] = task_arn
            task_execution.error_details = None

            success = True
        except ClientError as client_error:
            logger.warning(f'Failed to start Task {task.uuid}', exc_info=True)
            task_execution.error_details = client_error.response
        except Exception as ex:
            logger.warning(f'Failed to start Task {task.uuid}', exc_info=True)
            task_execution.error_details = {
                'exception': str(ex)
            }

        if not success:
            from ..models import Execution, TaskExecution
            task_execution.status = Execution.Status.FAILED
            task_execution.stop_reason = TaskExecution.StopReason.FAILED_TO_START
            task_execution.finished_at = timezone.now()

        task_execution.save()

    def make_aws_ecs_service_name(self, index: int = 0) -> str:
        if not self.task:
            raise APIException("make_aws_ecs_service_name(): missing Task")

        return 'CR_' + str(self.task.uuid) + '_' + str(index)

    def find_aws_ecs_service(self, ecs_client: Any | None=None,
            service_arn_or_name: str | None = None) -> AwsEcsServiceResponseFragment | None:
        if ecs_client is None:
            ecs_client = self.make_ecs_client()

        cluster = self.settings.cluster_arn

        if not cluster:
            logger.debug("find_aws_ecs_service(): No ECS Cluster found, returning None")
            return None

        if not service_arn_or_name:
            if self.service_settings:
                service_arn_or_name = self.service_settings.service_arn

            service_arn_or_name = service_arn_or_name or self.make_aws_ecs_service_name()

        logger.debug(f"describe_services() with {service_arn_or_name=}, {cluster=}")

        try:
            response_dict = ecs_client.describe_services(
                cluster=cluster,
                services=[service_arn_or_name])
            services = response_dict['services']

            if len(services) != 1:
                logger.info(f"No or multiple services named '{service_arn_or_name}' found for cluster '{cluster}'")
                return None

            return AwsEcsServiceResponseFragment.from_boto_service_response_fragment(
                    services[0])
        except Exception:
            logger.warning("Can't describe services", exc_info=True)
            return None

    def make_ecs_client(self):
        session_id = ''

        if self.task:
            if self.task.uuid:
                session_id = str(self.task.uuid)
            elif self.task.run_environment:
                session_id = str(self.task.run_environment.uuid)

        session_id = session_id or str(uuid.uuid4())

        return self.aws_settings.make_boto3_client('ecs', session_uuid=session_id)

    def delete_service(self, service_name: str, ecs_client: Any) -> AwsEcsServiceResponseFragment:
        logger.info(f"Deleting service '{service_name}' ...")
        deletion_response = ecs_client.delete_service(
            cluster=self.settings.cluster_arn,
            service=service_name,
            force=True)

        return AwsEcsServiceResponseFragment.from_boto_service_response_fragment(
                deletion_response['service'])

    def assign_public_ip_str(self) -> str:
        aws_network = self.aws_settings.network

        assign_public_ip = False

        if aws_network and aws_network.assign_public_ip:
            assign_public_ip = True

        if assign_public_ip:
            return 'ENABLED'

        return 'DISABLED'

    def make_common_args(self, include_launch_type: bool=True) -> dict[str, Any]:
        platform_version = self.settings.platform_version or AWS_ECS_PLATFORM_VERSION_LATEST

        subnets: list[str] = []
        security_groups: list[str] = []

        task_network = self.aws_settings.network

        if task_network:
            subnets = task_network.subnets or subnets
            security_groups = task_network.security_groups or security_groups

        # TODO: check if empty subnets is viable

        assign_public_ip = self.assign_public_ip_str()
        args = {
            'cluster': self.settings.cluster_arn,
            'taskDefinition': self.settings.task_definition_arn,
            'networkConfiguration': {
                'awsvpcConfiguration': {
                    'subnets': subnets,
                    'securityGroups': security_groups,
                    'assignPublicIp': assign_public_ip
                }
            },
            'platformVersion': platform_version,
        }

        if self.settings.capacity_provider_strategy:
            args['capacityProviderStrategy'] = self.settings.boto3_capacity_provider_strategy_value()
        elif include_launch_type:
            launch_type = self.settings.launch_type or self.DEFAULT_LAUNCH_TYPE

            if (self.settings.supported_launch_types is not None) and \
                 (launch_type not in self.settings.supported_launch_types):
                raise UnprocessableEntity(detail=f"Launch type '{launch_type}' is not supported")

            args['launchType'] = launch_type

        return args


    def make_common_service_args(self, include_launch_type: bool=True) -> dict[str, Any]:
        ecs_settings = self.settings
        ss = self.service_settings

        if not ss:
            raise RuntimeError('No service settings found')

        task = self.task

        if not task:
            raise RuntimeError('No Task found')

        args = self.make_common_args(include_launch_type=include_launch_type)
        args['desiredCount'] = task.service_instance_count

        managed_tags = ecs_settings.enable_ecs_managed_tags
        if managed_tags is not None:
            args['enableECSManagedTags'] = managed_tags

        propagate_tags = ecs_settings.propagate_tags
        if propagate_tags:
            args['propagateTags'] = propagate_tags

        dc = ss.deployment_configuration or AwsEcsServiceDeploymentConfiguration()
        dcb = dc.deployment_circuit_breaker or AwsEcsServiceDeploymentCircuitBreaker()

        dc_arg = dc.to_boto3_dict()

        dc_arg.update({        
            'maximumPercent': coalesce(dc.maximum_percent, 200),
            'minimumHealthyPercent': coalesce(dc.minimum_healthy_percent, 100),
            'deploymentCircuitBreaker': {
                'enable': coalesce(dcb.enable, False),
                'rollback': coalesce(dcb.rollback, False),
            }
        })

        args['deploymentConfiguration'] = dc_arg

        if ss.scheduling_strategy:
            args['schedulingStrategy'] = ss.scheduling_strategy

        if ss.load_balancers:
            args['loadBalancers'] = [lb.to_boto3_dict(main_container_name=self.settings.main_container_name) for lb in ss.load_balancers]                
            args['healthCheckGracePeriodSeconds'] = \
                ss.health_check_grace_period_seconds or \
                self.DEFAULT_LOAD_BALANCER_HEALTH_CHECK_GRACE_PERIOD_SECONDS

        service_registries = ss.service_registries
        if service_registries is not None:
            args['serviceRegistries'] = [sr.to_boto3_dict() for sr in service_registries]

        if ss.service_connect_configuration is not None:
            args['serviceConnectConfiguration'] = ss.service_connect_configuration.to_boto3_dict()

        if ss.volume_configurations is not None:
            args['volumes'] = [vc.to_boto3_dict() for vc in ss.volume_configurations]

        if ss.vpc_lattice_configurations is not None:
            args['vpcLatticeConfigurations'] = [vlc.to_boto3_dict() for vlc in ss.vpc_lattice_configurations]

        return args

    def add_creation_args(self, args: dict[str, Any], for_scheduled_task: bool = False,
            for_service: bool = False) -> dict[str, Any]:
        tags = self.compute_tags(for_scheduled_task=for_scheduled_task, for_service=for_service)

        if len(tags) > 0:
            args['tags']  = [
                { 'key': k, 'value': v } for k, v in tags.items() if v
            ][0:self.MAX_TAG_COUNT]

        return args

    def compute_tags(self, for_scheduled_task: bool = False, for_service: bool = False) -> dict[str, str]:
        output_tags = (self.aws_settings.tags or {}).copy()

        # TODO: add scheduled task tags

        if for_service and self.service_settings:
            output_tags.update(AwsTagKeyValuePair.pair_list_to_dict(self.service_settings.tags or []))

        return output_tags

    @override
    def sanitize_task_settings(self) -> bool:
        if not self.task:
            raise RuntimeError("No Task found")

        changed = super().sanitize_task_settings()

        if self.settings and self.settings.sanitize(self.aws_settings):
            self.task.execution_method_capability_details = self.settings.model_dump()
            changed = True

        return changed

    @override
    def enrich_task_settings(self) -> None:
        if not self.task:
            raise RuntimeError("No Task found")

        super().enrich_task_settings()

        emcd = self.task.execution_method_capability_details
        if emcd:
            aws_ecs_settings = AwsEcsExecutionMethodSettings.model_validate(emcd)
            aws_ecs_settings.update_derived_attrs(aws_settings=self.aws_settings)
            self.task.execution_method_capability_details = aws_ecs_settings.model_dump()

        if self.service_settings:
            self.service_settings.update_derived_attrs(aws_ecs_settings=self.settings,
                    aws_settings=self.aws_settings)
            self.task.service_settings = self.service_settings.model_dump()

    @override
    def enrich_task_execution_settings(self) -> None:
        if self.task_execution is None:
            raise APIException("enrich_task_settings(): Missing Task Execution")

        super().enrich_task_execution_settings()

        emd = self.task_execution.execution_method_details

        if emd:
            aws_ecs_settings = AwsEcsExecutionMethodInfo.model_validate(emd)
            aws_ecs_settings.update_derived_attrs(aws_settings=self.aws_settings)
            self.task_execution.execution_method_details = aws_ecs_settings.model_dump()
