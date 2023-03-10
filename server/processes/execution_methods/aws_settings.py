from typing import Optional, cast

import os
from urllib.parse import quote
import uuid

import boto3

from pydantic import BaseModel

from ..common.aws import *
from ..exception import UnprocessableEntity
from .infrastructure_settings import InfrastructureSettings
from .execution_method import ExecutionMethod


INFRASTRUCTURE_TYPE_AWS = 'AWS'


class AwsNetwork(BaseModel):
    network_mode: Optional[str] = None
    ip_v4_subnet_cidr_block: Optional[str] = None
    dns_servers: Optional[list[str]] = None
    dns_search_list: Optional[list[str]] = None
    private_dns_name: Optional[str] = None
    subnet_gateway_ip_v4_address: Optional[str] = None
    ip_v4_addresses: Optional[list[str]] = None
    mac_address: Optional[str] = None


class AwsNetworkSettings(BaseModel):
    region: Optional[str] = None
    availability_zone: Optional[str] = None
    subnets: Optional[list[str]] = None
    subnet_infrastructure_website_urls: Optional[list[str]] = None
    security_groups: Optional[list[str]] = None
    security_group_infrastructure_website_urls: Optional[list[str]] = None
    assign_public_ip: Optional[bool] = None
    networks: Optional[list[AwsNetwork]] = None

    def update_derived_attrs(self, aws_settings: 'AwsSettings',
          execution_method: Optional[ExecutionMethod] = None) -> None:
        region = self.compute_region(aws_settings=aws_settings,
            execution_method=execution_method)

        if region:
            if self.subnets is None:
                self.subnet_infrastructure_website_urls = None
            else:
                self.subnet_infrastructure_website_urls = [x for x in [
                    make_aws_console_subnet_url(subnet_name, region) \
                    for subnet_name in self.subnets] if x is not None]

            if self.security_groups is None:
                self.security_group_infrastructure_website_urls = None
            else:
                self.security_group_infrastructure_website_urls = [x for x in [
                    make_aws_console_security_group_url(security_group_name, region) \
                    for security_group_name in self.security_groups] if x is not None]
        else:
            self.subnet_infrastructure_website_urls = None
            self.security_group_infrastructure_website_urls = None


    def compute_region(self, aws_settings: 'AwsSettings',
            execution_method: Optional[ExecutionMethod] = None) -> Optional[str]:
        from .aws_base_execution_method import AwsBaseExecutionMethod

        region = self.region or aws_settings.region

        if (not region) and isinstance(execution_method, AwsBaseExecutionMethod):
            region = cast(AwsBaseExecutionMethod, execution_method).compute_region()

        return region


class AwsLogOptions(BaseModel):
    region: Optional[str] = None
    group: Optional[str] = None
    create_group: Optional[str] = None
    stream_prefix: Optional[str] = None
    stream: Optional[str] = None
    datetime_format: Optional[str] = None
    multiline_pattern: Optional[str] = None
    mode: Optional[str] = None
    max_buffer_size: Optional[str] = None
    stream_infrastructure_website_url: Optional[str] = None

    def update_derived_attrs(self, aws_settings: 'AwsSettings',
            execution_method: Optional[ExecutionMethod] = None) -> None:
        self.stream_infrastructure_website_url = None

        if self.stream and self.group:
            region = self.compute_region(aws_settings=aws_settings,
                execution_method=execution_method)
            if region:
                #https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Faws-python-scheduled-cron-project-dev-cronHandler/log-events/2022$252F07$252F21$252F$255B$2524LATEST$255D45d39af3414141b6a281315363aa33bf
                self.stream_infrastructure_website_url = \
                    f"https://{region}.console.aws.amazon.com/cloudwatch/home?" \
                    + f"region={region}#logsV2:log-groups/log-group/" \
                    + aws_encode(self.group) + '/log-events/' \
                    + aws_encode(self.stream)

    def compute_region(self, aws_settings: 'AwsSettings',
            execution_method: Optional[ExecutionMethod] = None) -> Optional[str]:
        from .aws_base_execution_method import AwsBaseExecutionMethod

        region = self.region or aws_settings.region

        if (not region) and isinstance(execution_method, AwsBaseExecutionMethod):
            region = cast(AwsBaseExecutionMethod, execution_method).compute_region()

        return region


class AwsLoggingSettings(BaseModel):
    driver: Optional[str] = None
    options: Optional[AwsLogOptions] = None
    infrastructure_website_url: Optional[str] = None

    def update_derived_attrs(self, aws_settings: 'AwsSettings',
            execution_method: Optional[ExecutionMethod]) -> None:
        self.infrastructure_website_url = None

        options = self.options
        if not (options and options.group):
            return

        region = self.compute_region(aws_settings=aws_settings,
                execution_method=execution_method)

        if region and (self.driver == 'awslogs'):
            limit = 2000 # TODO: make configurable
            lq = options.group
            self.infrastructure_website_url = \
                f"https://{region}.console.aws.amazon.com/cloudwatch/home?" \
                + f"region={region}#logs-insights:queryDetail=" \
                + "~(end~0~start~-86400~timeType~'RELATIVE~unit~'seconds~" \
                + f"editorString~'fields*20*40timestamp*2c*20*40message*2c*20*40logStream*0a*7c*20sort*20*40timestamp*20desc*0a*7c*20limit*20{limit}~isLiveTail~false~source~(~'" \
                + quote(lq, safe='').replace('%', '*') + '))'

            options.update_derived_attrs(aws_settings=aws_settings)


    def compute_region(self, aws_settings: 'AwsSettings',
            execution_method: Optional[ExecutionMethod] = None) -> Optional[str]:
        from .aws_base_execution_method import AwsBaseExecutionMethod

        region: Optional[str] = None
        options = self.options

        if options:
            region = options.region

        if not region:
            region = aws_settings.region

        if (not region) and isinstance(execution_method, AwsBaseExecutionMethod):
            region = cast(AwsBaseExecutionMethod, execution_method).compute_region()

        return region


class AwsXraySettings(BaseModel):
    trace_id: Optional[str] = None
    context_missing: Optional[str] = None


PROTECTED_AWS_SETTINGS_PROPERTIES = [
  'secret_key',
]


class AwsSettings(InfrastructureSettings):
    account_id: Optional[str] = None
    region: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    events_role_arn: Optional[str] = None
    events_role_infrastructure_website_url: Optional[str] = None
    assumed_role_external_id: Optional[str] = None
    execution_role_arn: Optional[str] = None
    execution_role_infrastructure_website_url: Optional[str] = None
    workflow_starter_lambda_arn: Optional[str] = None
    workflow_starter_lambda_infrastructure_website_url: Optional[str] = None
    workflow_starter_access_key: Optional[str] = None
    network: Optional[AwsNetworkSettings] = None
    logging: Optional[AwsLoggingSettings] = None
    xray: Optional[AwsXraySettings] = None
    tags: Optional[dict[str, str]] = None

    def assume_aws_role(self, b, service_name: str, role_arn: str,
            region_name: str, session_uuid: str,
            aws_access_key: Optional[str] = None,
            aws_secret_access_key: Optional[str] = None,
            external_id: Optional[str] = None) -> boto3.session.Session:
        kwargs = {
            'region_name': region_name
        }

        if aws_access_key:
            kwargs['aws_access_key_id'] = aws_access_key

            if not aws_secret_access_key:
                raise UnprocessableEntity(detail='AWS access key found but not secret access key')

            kwargs['aws_secret_access_key'] = aws_secret_access_key

        sts_client = b.client('sts', **kwargs)

        logger.info(f"Assuming role {role_arn} ...")

        kwargs = {
            'RoleArn': role_arn,
            'RoleSessionName': f"{session_uuid}_{service_name}"
        }

        if external_id:
            kwargs['ExternalId'] = external_id

        assume_role_response = sts_client.assume_role(**kwargs)

        logger.info(f"Successfully assumed role {role_arn}.")

        assumed_credentials = assume_role_response['Credentials']

        return boto3.session.Session(
            aws_access_key_id=assumed_credentials['AccessKeyId'],
            aws_secret_access_key=assumed_credentials['SecretAccessKey'],
            aws_session_token=assumed_credentials['SessionToken'],
            region_name=region_name)


    def make_boto3_client(self, service_name: str, session_uuid: Optional[str] = None):
        if not self.region:
            raise UnprocessableEntity(detail='Missing region to access AWS')

        if self.access_key and self.secret_key:
            return boto3.client(
                service_name,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )  # type: ignore
        else:
            if not self.events_role_arn:
                raise UnprocessableEntity(detail='Missing IAM Role to access AWS')

            if not session_uuid:
                session_uuid = str(uuid.uuid4())

            customer_invoker_role_arn = os.environ['CUSTOMER_INVOKER_ROLE_ARN']
            aws_region = os.environ['HOME_AWS_DEFAULT_REGION']
            aws_access_key = os.environ.get('HOME_AWS_ACCESS_KEY')
            aws_secret_access_key = os.environ.get('HOME_AWS_SECRET_KEY')

            boto3_session_1 = self.assume_aws_role(boto3,
                service_name='sts',
                role_arn=customer_invoker_role_arn,
                region_name=aws_region,
                session_uuid=session_uuid,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key)

            boto3_session_2 = self.assume_aws_role(boto3_session_1,
                service_name=service_name,
                role_arn=self.events_role_arn,
                region_name=self.region,
                session_uuid=session_uuid,
                external_id=self.assumed_role_external_id)

            return boto3_session_2.client(service_name)  # type: ignore


    def make_events_client(self, session_uuid: Optional[str] = None):
        return self.make_boto3_client('events',
                session_uuid=session_uuid)

    def can_manage_infrastructure(self) -> bool:
        return bool(self.account_id and self.region and \
                ((self.events_role_arn and self.assumed_role_external_id) or
                (self.access_key and self.secret_key)))

    def can_schedule_workflow(self) -> bool:
        return self.can_manage_infrastructure() and bool(
                self.workflow_starter_lambda_arn and \
                self.workflow_starter_access_key and \
                self.execution_role_arn)

    def update_derived_attrs(self, execution_method: Optional[ExecutionMethod]=None) -> None:
        self.events_role_infrastructure_website_url = \
                make_aws_console_role_url(self.events_role_arn)

        self.execution_role_infrastructure_website_url = \
                make_aws_console_role_url(self.execution_role_arn)

        self.workflow_starter_lambda_infrastructure_website_url = \
                make_aws_console_lambda_function_url(self.workflow_starter_lambda_arn)

        if self.network:
            self.network.update_derived_attrs(aws_settings=self,
                  execution_method=execution_method)

        if self.logging:
            self.logging.update_derived_attrs(aws_settings=self,
                  execution_method=execution_method)
