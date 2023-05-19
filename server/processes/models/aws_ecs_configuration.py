from typing import List, Optional

import logging

from django.db import models

from django.contrib.postgres.fields import ArrayField

from .aws_tagged_entity import AwsTaggedEntity


logger = logging.getLogger(__name__)


class AwsEcsConfiguration(AwsTaggedEntity):
    PLATFORM_VERSION_DEFAULT = '1.4.0'
    PLATFORM_VERSION_LATEST = 'LATEST'
    ALLOWED_PLATFORM_VERSION_CHOICES = [
        '1.3.0',
        '1.4.0',
        PLATFORM_VERSION_LATEST,
    ]

    class Meta:
        abstract = True

    aws_default_subnets = ArrayField(
            models.CharField(max_length=1000, blank=False),
            blank=True, null=True)
    aws_ecs_default_security_groups = ArrayField(
            models.CharField(max_length=1000), blank=True, null=True)
    aws_ecs_default_assign_public_ip = models.BooleanField(default=False, null=True)
    aws_ecs_default_launch_type = models.CharField(max_length=50, blank=True)
    aws_ecs_supported_launch_types = ArrayField(
            models.CharField(max_length=50), blank=True, null=True)
    aws_ecs_default_cluster_arn = models.CharField(max_length=1000, blank=True)
    aws_ecs_default_execution_role = models.CharField(max_length=200,
            blank=True)
    aws_ecs_default_task_role = models.CharField(max_length=200, blank=True)

    aws_ecs_default_platform_version = models.CharField(max_length=10,
            blank=True, choices=[(x, x) for x in ALLOWED_PLATFORM_VERSION_CHOICES],
            default=PLATFORM_VERSION_DEFAULT)

    aws_ecs_enable_ecs_managed_tags = models.BooleanField(blank=True,
            null=True)

    def get_aws_region(self) -> Optional[str]:
        raise Exception('Not implemented')

    @property
    def aws_subnet_infrastructure_website_urls(self) -> Optional[List[Optional[str]]]:
        from ..common.aws import make_aws_console_subnet_url
        if not self.aws_default_subnets:
            return None

        aws_region = self.get_aws_region()
        return [make_aws_console_subnet_url(subnet_name, aws_region) \
                for subnet_name in self.aws_default_subnets]

    @property
    def aws_security_group_infrastructure_website_urls(self) -> Optional[List[Optional[str]]]:
        from ..common.aws import make_aws_console_security_group_url
        if not self.aws_ecs_default_security_groups:
            return None

        aws_region = self.get_aws_region()
        return [make_aws_console_security_group_url(security_group_name, aws_region) \
                for security_group_name in self.aws_ecs_default_security_groups]

    @property
    def aws_ecs_cluster_infrastructure_website_url(self) -> Optional[str]:
        from ..common.aws import make_aws_console_ecs_cluster_url
        return make_aws_console_ecs_cluster_url(
            self.aws_ecs_default_cluster_arn)

    @property
    def aws_ecs_execution_role_infrastructure_website_url(self) -> Optional[str]:
        from ..common.aws import make_aws_console_role_url
        return make_aws_console_role_url(self.aws_ecs_default_execution_role)

    @property
    def aws_ecs_task_role_infrastructure_website_url(self) -> Optional[str]:
        from ..common.aws import make_aws_console_role_url
        return make_aws_console_role_url(self.aws_ecs_default_task_role)
