from processes.execution_methods import UnknownExecutionMethod

from processes.models import Task
from processes.execution_methods import (
    INFRASTRUCTURE_TYPE_AWS,
)

from processes.execution_methods.aws_ecs_execution_method import (
      AWS_ECS_PLATFORM_VERSION_DEFAULT,
      AwsEcsExecutionMethod,
      AwsEcsExecutionMethodSettings,      
)

import factory
from faker import Factory as FakerFactory

from .owned_model_factory import OwnedModelFactory
from .run_environment_factory import RunEnvironmentFactory

faker = FakerFactory.create()


class TaskFactory(OwnedModelFactory):
    class Meta:
        model = Task

    name = factory.Sequence(lambda n: f'task_{n}')

    max_manual_start_delay_before_alert_seconds = 600
    max_manual_start_delay_before_abandonment_seconds = 1200
    heartbeat_interval_seconds = 300
    max_heartbeat_lateness_before_alert_seconds = 120
    max_heartbeat_lateness_before_abandonment_seconds = 600
    service_instance_count: int | None = None
    min_service_instance_count: int | None = None
    max_age_seconds: int | None = None
    default_max_retries = 2

    environment_variables_overrides = None
    project_url = 'https://github.com/cloudreactor/coolproj'
    log_query = '/aws/fargate/coolproj-production'
    run_environment = factory.SubFactory(RunEnvironmentFactory,
        created_by_user=factory.SelfAttribute("..created_by_user"),
        created_by_group=factory.SelfAttribute("..created_by_group"))

    enabled = True
    other_metadata = None
    latest_task_execution = None
    was_auto_created = False
    passive = False

    execution_method_type = AwsEcsExecutionMethod.NAME

    is_scheduling_managed = None
    is_service_managed = None

    managed_probability = 1.0
    failure_report_probability = 1.0
    timeout_report_probability = 1.0

    execution_method_capability_details = AwsEcsExecutionMethodSettings(
        launch_type = AwsEcsExecutionMethod.DEFAULT_LAUNCH_TYPE,
        supported_launch_types = [AwsEcsExecutionMethod.DEFAULT_LAUNCH_TYPE],
        task_definition_arn = 'arn:aws:ecs:us-west-2:123456789012:task-definition/hello_world:8',        
        platform_version = AWS_ECS_PLATFORM_VERSION_DEFAULT,
    ).model_dump()

    infrastructure_type = INFRASTRUCTURE_TYPE_AWS

    # aws_ecs_service_updated_at = None

    allocated_cpu_units: int | None = 512
    allocated_memory_mb: int | None = 2048


class UnknownTaskFactory(TaskFactory):
    execution_method_type = UnknownExecutionMethod.NAME

    allocated_cpu_units = None
    allocated_memory_mb = None

    was_auto_created = True
    passive = True
