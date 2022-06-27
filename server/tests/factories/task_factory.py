from typing import Optional

from processes.execution_methods.aws_ecs_execution_method import AwsEcsExecutionMethod
from processes.models import Task
from processes.models.convert_legacy_em_and_infra import populate_task_emc_and_infra

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
    service_instance_count: Optional[int] = None
    min_service_instance_count: Optional[int] = None
    max_age_seconds: Optional[int] = None
    default_max_retries = 2

    environment_variables_overrides = None
    project_url = 'https://github.com/cloudreactor/coolproj'
    log_query = '/aws/fargate/coolproj-production'
    run_environment = factory.SubFactory(RunEnvironmentFactory,
        created_by_user=factory.SelfAttribute("..created_by_user"),
        created_by_group=factory.SelfAttribute("..created_by_group"))

    other_metadata = None
    latest_task_execution = None
    was_auto_created = False
    passive = False

    execution_method_type = AwsEcsExecutionMethod.NAME

    aws_default_subnets: Optional[list[str]] = None
    aws_ecs_task_definition_arn = 'arn:aws:ecs:us-west-2:123456789012:task-definition/hello_world:8'
    aws_ecs_default_launch_type = 'FARGATE'
    aws_ecs_supported_launch_types: Optional[list[str]] = ['FARGATE']
    aws_ecs_default_cluster_arn = ''
    aws_ecs_default_security_groups: Optional[list[str]] = None
    aws_ecs_default_assign_public_ip = False
    aws_ecs_service_load_balancer_health_check_grace_period_seconds: Optional[int] = None
    aws_ecs_default_execution_role = ''
    aws_ecs_default_task_role = ''
    aws_ecs_main_container_name = ''
    aws_scheduled_execution_rule_name = ''
    aws_scheduled_event_rule_arn = ''
    aws_event_target_rule_name = ''
    aws_event_target_id = ''
    aws_ecs_service_arn = ''
    aws_ecs_service_updated_at = None

    allocated_cpu_units: Optional[int] = 512
    allocated_memory_mb: Optional[int] = 2048

    @factory.post_generation
    def sanitize_emc(task: Task, create: bool, extracted, **kwargs):
        if task.execution_method_capability_details:
            return

        populate_task_emc_and_infra(task)
