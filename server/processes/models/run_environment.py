from typing import Optional, Type, TYPE_CHECKING

import logging

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from ..exception.unprocessable_entity import UnprocessableEntity
from ..execution_methods import (
    AwsSettings,
    AwsEcsExecutionMethodSettings,
    AwsLambdaExecutionMethodSettings
)
from .named_with_uuid_model import NamedWithUuidModel

from .aws_ecs_configuration import AwsEcsConfiguration
from .infrastructure_configuration import InfrastructureConfiguration
from .subscription import Subscription

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from .alert_method import AlertMethod
    from .notification_profile import NotificationProfile


class RunEnvironment(InfrastructureConfiguration, AwsEcsConfiguration,
        NamedWithUuidModel):
    class Meta:
        unique_together = (('name', 'created_by_group'),)

    aws_settings = models.JSONField(null=True, blank=True)

    # Deprecated
    aws_account_id = models.CharField(max_length=200, blank=True)
    aws_default_region = models.CharField(max_length=20, blank=True)
    aws_access_key = models.CharField(max_length=100, blank=True)
    aws_secret_key = models.CharField(max_length=100, blank=True)
    aws_events_role_arn = models.CharField(max_length=100, blank=True)
    aws_assumed_role_external_id = models.CharField(max_length=1000, blank=True)
    aws_workflow_starter_lambda_arn = models.CharField(max_length=1000, blank=True)
    aws_workflow_starter_access_key = models.CharField(max_length=1000, blank=True)
    # End deprecated

    default_aws_ecs_configuration = models.JSONField(null=True, blank=True)
    default_aws_lambda_configuration = models.JSONField(null=True, blank=True)

    # Deprecated
    default_alert_methods = models.ManyToManyField('AlertMethod', blank=True)

    notification_profiles = models.ManyToManyField('NotificationProfile')

    # Deprecated, use InfrastructureSettings.can_manage_infrastructure()
    def can_control_aws_ecs(self) -> bool:
        if not self.aws_settings:
            return False

        aws_settings = AwsSettings.parse_obj(self.aws_settings)
        return aws_settings.can_manage_infrastructure()

    # Deprecated, use AwsSettings.region
    def get_aws_region(self) -> Optional[str]:
        if self.aws_settings:
            return self.aws_settings.get('region')

        return None

    # Deprecated, use AwsSettings.make_boto3_client()
    def make_boto3_client(self, service_name: str):
        if not self.aws_settings:
            raise RuntimeError("make_boto3_client(): no AWS settings found")

        aws_settings = AwsSettings.parse_obj(self.aws_settings)
        return aws_settings.make_boto3_client(service_name=service_name,
                session_uuid=str(self.uuid))

    def can_schedule_workflow(self) -> bool:
        if not self.aws_settings:
            return False

        aws_settings = AwsSettings.parse_obj(self.aws_settings)
        return aws_settings.can_schedule_workflow()

    def enrich_settings(self) -> None:
        aws_settings: Optional[AwsSettings] = None
        if self.aws_settings:
            aws_settings = AwsSettings.parse_obj(self.aws_settings)
            aws_settings.update_derived_attrs()
            self.aws_settings = aws_settings.dict()

        if self.default_aws_ecs_configuration:
            aws_ecs_settings = AwsEcsExecutionMethodSettings.parse_obj(self.default_aws_ecs_configuration)
            aws_ecs_settings.update_derived_attrs(aws_settings=aws_settings)
            self.default_aws_ecs_configuration = aws_ecs_settings.dict()

        if self.default_aws_lambda_configuration:
            aws_lambda_settings = AwsLambdaExecutionMethodSettings.parse_obj(self.default_aws_lambda_configuration)
            aws_lambda_settings.update_derived_attrs(aws_settings=aws_settings)
            self.default_aws_lambda_configuration = aws_lambda_settings.dict()



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

    try:
        instance.enrich_settings()
    except Exception as ex:
        logger.warning(f"Failed to enrich Run Environment {instance.uuid} settings", exc_info=ex)
