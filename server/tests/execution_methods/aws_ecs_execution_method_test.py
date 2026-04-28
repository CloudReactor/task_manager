import pytest

from moto import mock_aws

from conftest import setup_aws, setup_aws_ecs, validate_aws_ecs_task_settings

from processes.execution_methods.aws_cloudwatch_scheduling_settings import (
    SCHEDULING_TYPE_AWS_CLOUDWATCH, AwsCloudwatchSchedulingSettings
)
from processes.execution_methods.aws_ecs_execution_method import (
    AwsEcsExecutionMethod,
    AwsEcsServiceSettings,
    SERVICE_PROVIDER_AWS_ECS,
)


@pytest.mark.django_db
@mock_aws
@pytest.mark.parametrize("""
    use_cluster_name_instead_of_arn
""", [
    (True),
    (False),
])                      
def test_aws_ecs_scheduled_task_execution_setup_and_teardown(use_cluster_name_instead_of_arn: bool, 
        run_environment_factory, task_factory):
    run_env = run_environment_factory()
    aws_settings = setup_aws()

    run_env.aws_settings = aws_settings.model_dump()
    aws_ecs_setup = setup_aws_ecs(run_env)
    run_env.save()

    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME, run_environment=run_env)
    task.execution_method_capability_details = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.save()
    
    assert task.enabled is True
    assert task.scheduling_settings is None

    task.schedule = 'rate(5 minutes)'
    task.schedule_provider = SCHEDULING_TYPE_AWS_CLOUDWATCH
    task.scheduled_instance_count = 1

    if use_cluster_name_instead_of_arn:
        emc = task.execution_method_capability_details.copy()
        emc['cluster_arn'] = aws_ecs_setup.cluster_name
        task.execution_method_capability_details = emc

    task.save()

    assert task.schedule_provider == SCHEDULING_TYPE_AWS_CLOUDWATCH
    assert task.scheduled_instance_count == 1
    assert task.schedule_updated_at is not None
    
    ss_dict = task.scheduling_settings

    assert ss_dict is not None
    ss = AwsCloudwatchSchedulingSettings.model_validate(ss_dict)

    assert task.has_active_managed_scheduled_execution() is True
    assert ss.event_rule_arn.startswith('arn:aws:events:')
    assert ss.event_target_id is not None
    assert ss.event_target_rule_name is not None

    validate_aws_ecs_task_settings(model_task=task, aws_settings=aws_settings, 
            aws_ecs_setup=aws_ecs_setup)

    # Tear down clearing the schedule
    task.schedule = ''
    task.save()

    assert task.has_active_managed_scheduled_execution() is False

    validate_aws_ecs_task_settings(model_task=task, aws_settings=aws_settings, 
            aws_ecs_setup=aws_ecs_setup)

@pytest.mark.django_db
@pytest.mark.parametrize("""
    use_cluster_name_instead_of_arn
""", [
    (True),
    (False),
])                      
@mock_aws
def test_aws_ecs_service_task_setup_and_teardown(use_cluster_name_instead_of_arn, task_factory):
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)

    run_env = task.run_environment
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()

    aws_ecs_setup = setup_aws_ecs(run_env)

    task.execution_method_capability_details = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.save()

    assert task.enabled is True
    assert task.is_service is False
    assert task.service_settings is None

    # Enable the task as a managed service

    if use_cluster_name_instead_of_arn:
        emc = task.execution_method_capability_details.copy()
        emc['cluster_arn'] = aws_ecs_setup.cluster_name
        task.execution_method_capability_details = emc

    task.service_instance_count = 2
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()

    assert task.is_service is True
    assert task.is_service_managed is True
    assert task.aws_ecs_service_updated_at is not None

    ss_dict = task.service_settings
    assert ss_dict is not None

    validate_aws_ecs_task_settings(model_task=task, aws_settings=aws_settings, 
            aws_ecs_setup=aws_ecs_setup)

    ss = AwsEcsServiceSettings.model_validate(ss_dict)
    assert ss.service_arn is not None
    assert ss.service_arn.startswith('arn:aws:ecs:')

    # Tear down by disabling the service
    task.service_instance_count = None
    task.save()    

    assert task.is_service is False
    assert task.is_service_managed is None

    validate_aws_ecs_task_settings(model_task=task, aws_settings=aws_settings, 
            aws_ecs_setup=aws_ecs_setup)