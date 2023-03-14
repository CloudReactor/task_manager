from typing import Optional, Type

import logging
import os

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

import boto3

from ..exception.unprocessable_entity import UnprocessableEntity

from .named_with_uuid_model import NamedWithUuidModel
from .aws_ecs_configuration import AwsEcsConfiguration
from .infrastructure_configuration import InfrastructureConfiguration
from .subscription import Subscription

logger = logging.getLogger(__name__)


class RunEnvironment(InfrastructureConfiguration, AwsEcsConfiguration,
        NamedWithUuidModel):
    class Meta:
        unique_together = (('name', 'created_by_group'),)

    aws_settings = models.JSONField(null=True, blank=True)

    aws_account_id = models.CharField(max_length=200, blank=True)
    aws_default_region = models.CharField(max_length=20, blank=True)
    aws_access_key = models.CharField(max_length=100, blank=True)
    aws_secret_key = models.CharField(max_length=100, blank=True)
    aws_events_role_arn = models.CharField(max_length=100, blank=True)
    aws_assumed_role_external_id = models.CharField(max_length=1000, blank=True)

    default_aws_ecs_configuration = models.JSONField(null=True, blank=True)

    aws_workflow_starter_lambda_arn = models.CharField(max_length=1000, blank=True)
    aws_workflow_starter_access_key = models.CharField(max_length=1000, blank=True)
    default_alert_methods = models.ManyToManyField('AlertMethod', blank=True)

    def can_control_aws_ecs(self) -> bool:
        return bool(self.aws_account_id and self.aws_default_region and \
                ((self.aws_events_role_arn and \
                self.aws_assumed_role_external_id) or
                (self.aws_access_key and self.aws_secret_key)))

    def get_aws_region(self) -> str:
        return self.aws_default_region

    def assume_aws_role(self, b, service_name: str, role_arn: str,
            region_name: str,
            aws_access_key: Optional[str] = None,
            aws_secret_access_key: Optional[str] = None,
            external_id: Optional[str] = None) -> boto3.session.Session:
        kwargs = dict(
            region_name=region_name
        )

        if aws_access_key:
            kwargs['aws_access_key_id'] = aws_access_key

            if not aws_secret_access_key:
                raise Exception('AWS access key found but not secret access key')

            kwargs['aws_secret_access_key'] = aws_secret_access_key

        sts_client = b.client('sts', **kwargs)

        logger.info(f"Assuming role {role_arn} ...")

        kwargs = dict(
            RoleArn=role_arn,
            RoleSessionName=f"{self.uuid}_{service_name}"
        )

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

    def make_boto3_client(self, service_name: str):
        if self.aws_access_key and self.aws_secret_key:
            return boto3.client(
                service_name,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_default_region
            )  # type: ignore
        else:
            customer_invoker_role_arn = os.environ['CUSTOMER_INVOKER_ROLE_ARN']
            aws_region = os.environ['HOME_AWS_DEFAULT_REGION']
            aws_access_key = os.environ.get('HOME_AWS_ACCESS_KEY')
            aws_secret_access_key = os.environ.get('HOME_AWS_SECRET_KEY')

            boto3_session_1 = self.assume_aws_role(boto3,
                service_name='sts',
                role_arn=customer_invoker_role_arn,
                region_name=aws_region,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key)

            boto3_session_2 = self.assume_aws_role(boto3_session_1,
                service_name=service_name,
                role_arn=self.aws_events_role_arn,
                region_name=self.aws_default_region,
                external_id=self.aws_assumed_role_external_id)

            return boto3_session_2.client(service_name)  # type: ignore

    def can_schedule_workflow(self) -> bool:
        return bool(self.aws_account_id and \
                self.aws_workflow_starter_lambda_arn and \
                self.aws_workflow_starter_access_key and \
                self.aws_ecs_default_execution_role)


@receiver(pre_save, sender=RunEnvironment)
def pre_save_run_environment(sender: Type[RunEnvironment], **kwargs):
    instance = kwargs['instance']
    logger.info(f"pre-save with Run Environment {instance}")

    if instance.pk is None:
        usage_limits = Subscription.compute_usage_limits(instance.created_by_group)

        # For now use the Task limit for Run Environments
        max_tasks = usage_limits.max_tasks

        existing_count = RunEnvironment.objects.filter(
                created_by_group=instance.created_by_group).count()

        if (max_tasks is not None) and (existing_count >= max_tasks):
            raise UnprocessableEntity(detail='Task limit exceeded', code='limit_exceeded')

    from .convert_legacy_em_and_infra import (
        populate_run_environment_infra,
        populate_run_environment_aws_ecs_configuration
    )

    # Temporary until the JSON fields are the source of truth
    populate_run_environment_infra(instance)
    populate_run_environment_aws_ecs_configuration(instance)
