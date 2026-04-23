from __future__ import annotations

from typing import Type, override, TYPE_CHECKING

import logging

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from ..exception.unprocessable_entity import UnprocessableEntity
from ..execution_methods import (
    AwsSettings,
    AwsEcsExecutionMethodSettings,
    AwsLambdaExecutionMethodSettings,
    InfrastructureSettings,
)
from .named_with_uuid_model import NamedWithUuidModel
from .infrastructure_configuration import InfrastructureConfiguration
from .subscription import Subscription

if TYPE_CHECKING:
    from ..execution_methods.execution_method import ExecutionMethodSettings
    from .notification_profile import NotificationProfile    

logger = logging.getLogger(__name__)


class RunEnvironment(InfrastructureConfiguration, NamedWithUuidModel):
    class Meta:
        unique_together = (('name', 'created_by_group'),)

    aws_settings = models.JSONField(null=True, blank=True)

    default_aws_ecs_configuration = models.JSONField(null=True, blank=True)
    default_aws_lambda_configuration = models.JSONField(null=True, blank=True)

    notification_profiles: models.ManyToManyField['NotificationProfile', 'NotificationProfile'] = models.ManyToManyField('NotificationProfile')

    @override
    def parsed_infrastructure_settings(self) -> InfrastructureSettings | None:
        return self.parsed_aws_settings()

    def parsed_aws_settings(self) -> AwsSettings | None:
        if not self.aws_settings:
            return None

        return AwsSettings.model_validate(self.aws_settings)


    def parsed_execution_method_settings(self, method_type: str) -> ExecutionMethodSettings | None:
        from ..execution_methods.aws_ecs_execution_method import (
            AwsEcsExecutionMethod, AwsEcsExecutionMethodSettings
        )
        from ..execution_methods.aws_lambda_execution_method import (
            AwsLambdaExecutionMethod, AwsLambdaExecutionMethodSettings
        )

        if method_type == AwsEcsExecutionMethod.NAME:
            if not self.default_aws_ecs_configuration:
                return None

            return AwsEcsExecutionMethodSettings.model_validate(self.default_aws_ecs_configuration)
        elif method_type == AwsLambdaExecutionMethod.NAME:
            if not self.default_aws_lambda_configuration:
                return None

            return AwsLambdaExecutionMethodSettings.model_validate(self.default_aws_lambda_configuration)
        else:
            return None


    def can_schedule_workflow(self) -> bool:
        infra_settings = self.parsed_infrastructure_settings()
        return (infra_settings is not None) and infra_settings.can_schedule_workflow()

    def enrich_settings(self) -> None:
        aws_settings = self.parsed_aws_settings()
        if aws_settings:
            aws_settings.update_derived_attrs()
            self.aws_settings = aws_settings.model_dump()

        if self.default_aws_ecs_configuration:
            aws_ecs_settings = AwsEcsExecutionMethodSettings.model_validate(self.default_aws_ecs_configuration)
            aws_ecs_settings.update_derived_attrs(aws_settings=aws_settings)
            self.default_aws_ecs_configuration = aws_ecs_settings.model_dump()

        if self.default_aws_lambda_configuration:
            aws_lambda_settings = AwsLambdaExecutionMethodSettings.model_validate(self.default_aws_lambda_configuration)
            aws_lambda_settings.update_derived_attrs(aws_settings=aws_settings)
            self.default_aws_lambda_configuration = aws_lambda_settings.model_dump()



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
