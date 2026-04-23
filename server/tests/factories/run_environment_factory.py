
from processes.execution_methods.aws_ecs_execution_method import (
  AWS_ECS_PLATFORM_VERSION_DEFAULT,
  AwsEcsExecutionMethod, AwsEcsExecutionMethodSettings
)
from processes.execution_methods.aws_settings import INFRASTRUCTURE_TYPE_AWS, AwsSettings, AwsNetworkSettings
from processes.models import RunEnvironment

import factory
from faker import Factory as FakerFactory

from .owned_model_factory import OwnedModelFactory

faker = FakerFactory.create()


class RunEnvironmentFactory(OwnedModelFactory):
    class Meta:
        model = RunEnvironment

    name = factory.Sequence(lambda n: f'run_environment_{n}')

    @factory.post_generation
    def sanitize_infra_and_aws_ecs_configuration(run_environment: RunEnvironment, create: bool, extracted, **kwargs):
        if not run_environment.infrastructure_type:
            run_environment.infrastructure_type = INFRASTRUCTURE_TYPE_AWS

        if (run_environment.infrastructure_type == INFRASTRUCTURE_TYPE_AWS) and \
                not run_environment.aws_settings:
            run_environment.aws_settings = AwsSettings(
                account_id='123456789012',
                region='us-west-1',
                events_role_arn='arn:aws:iam::123456789012:role/cloudreactor_assumable',
                assumed_role_external_id='DEADBEEF',
                execution_role_arn='arn:aws:iam::123456789012:role/execution',
                workflow_starter_lambda_arn='arn:aws:lambda:us-west-1:123456789012:function:workflow_starter',
                workflow_starter_access_key='WSAKIADEADBEEF',
                network=AwsNetworkSettings(
                    region='us-west-1',
                    availability_zone='us-west-1a',
                    subnets=['subnet-123456'],
                    security_groups=['sg-123456'],
                    assign_public_ip=False
                ),
                tags={
                    'Tag1': 'A',
                    'Tag2': 'B',
                }
            ).model_dump()

        if not run_environment.default_aws_ecs_configuration:
            run_environment.default_aws_ecs_configuration = AwsEcsExecutionMethodSettings(
                launch_type = AwsEcsExecutionMethod.DEFAULT_LAUNCH_TYPE,
                supported_launch_types = [AwsEcsExecutionMethod.DEFAULT_LAUNCH_TYPE],                
                cluster_arn='arn:aws:ecs:us-west-1:123456789012:cluster/MyECSCluster',
                execution_role_arn='arn:aws:iam::123456789012:role/execution',
                platform_version = AWS_ECS_PLATFORM_VERSION_DEFAULT,
            ).model_dump()

        run_environment.save()
