from typing import Optional, TYPE_CHECKING

from urllib.parse import quote

from pydantic import BaseModel

from ..common.aws import aws_encode


if TYPE_CHECKING:
    from ..models import (
      RunEnvironment
    )


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

    def update_derived_attrs(self, run_environment: 'RunEnvironment') -> None:
        from ..common.aws import (
            make_aws_console_subnet_url,
            make_aws_console_security_group_url
        )
        region = self.region or run_environment.get_aws_region()

        if region:
            if self.subnets is None:
                self.subnet_infrastructure_website_urls = None
            else:
                self.subnet_infrastructure_website_urls = [
                    make_aws_console_subnet_url(subnet_name, region) \
                    for subnet_name in self.subnets]

            if self.security_groups is None:
                self.security_group_infrastructure_website_urls = None
            else:
                self.security_group_infrastructure_website_urls = [
                    make_aws_console_security_group_url(security_group_name, region) \
                    for security_group_name in self.security_groups]
        else:
            self.subnet_infrastructure_website_urls = None
            self.security_group_infrastructure_website_urls = None


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

    def update_derived_attrs(self, run_environment: 'RunEnvironment') -> None:
        self.stream_infrastructure_website_url = None

        if self.stream and self.group:
            region = self.region or run_environment.aws_default_region

            if region:
                #https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Faws-python-scheduled-cron-project-dev-cronHandler/log-events/2022$252F07$252F21$252F$255B$2524LATEST$255D45d39af3414141b6a281315363aa33bf
                self.stream_infrastructure_website_url = \
                    f"https://{region}.console.aws.amazon.com/cloudwatch/home?" \
                    + f"region={region}#logsV2:log-groups/log-group/" \
                    + aws_encode(self.group) + '/log-events/' \
                    + aws_encode(self.stream)


class AwsLoggingSettings(BaseModel):
    driver: Optional[str] = None
    options: Optional[AwsLogOptions] = None
    infrastructure_website_url: Optional[str] = None

    def update_derived_attrs(self, run_environment: 'RunEnvironment') -> None:
        self.infrastructure_website_url = None

        options = self.options
        if not (options and options.group):
            return

        region = options.region or run_environment.aws_default_region
        if region and (self.driver == 'awslogs'):
            limit = 2000 # TODO: make configurable
            lq = options.group
            self.infrastructure_website_url = \
                f"https://{region}.console.aws.amazon.com/cloudwatch/home?" \
                + f"region={region}#logs-insights:queryDetail=" \
                + "~(end~0~start~-86400~timeType~'RELATIVE~unit~'seconds~" \
                + f"editorString~'fields*20*40timestamp*2c*20*40message*0a*7c*20sort*20*40timestamp*20desc*0a*7c*20limit*20{limit}~isLiveTail~false~source~(~'" \
                + quote(lq, safe='').replace('%', '*') + '))'

            options.update_derived_attrs(run_environment=run_environment)

class AwsXraySettings(BaseModel):
    trace_id: Optional[str] = None
    context_missing: Optional[str] = None


class AwsSettings(BaseModel):
    network: Optional[AwsNetworkSettings] = None
    logging: Optional[AwsLoggingSettings] = None
    xray: Optional[AwsXraySettings] = None
    tags: Optional[dict[str, str]] = None

    def update_derived_attrs(self, run_environment: 'RunEnvironment') -> None:
        if self.network:
            self.network.update_derived_attrs(run_environment=run_environment)

        if self.logging:
            self.logging.update_derived_attrs(run_environment=run_environment)
