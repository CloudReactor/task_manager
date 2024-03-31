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
