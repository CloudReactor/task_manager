
from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel

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
                self.security_group_infrastructure_website_urls = [
                    make_aws_console_security_group_url(security_group_name, region) \
                    for security_group_name in self.security_groups]
            else:
                self.security_group_infrastructure_website_urls = None
        else:
            self.subnet_infrastructure_website_urls = None
            self.security_group_infrastructure_website_urls = None

class AwsLogOptions(BaseModel):
    group: Optional[str] = None
    region: Optional[str] = None
    stream: Optional[str] = None


class AwsLoggingSettings(BaseModel):
    driver: Optional[str] = None
    options: Optional[AwsLogOptions] = None


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