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
from processes.models.task import Task


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


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_no_old_execution_method(task_factory):
    """Test when there's no old execution method (first time creating service)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task.execution_method_capability_details = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    execution_method = AwsEcsExecutionMethod(task=task)
    should_update, should_recreate = execution_method.should_update_or_force_recreate_service(old_execution_method=None)
    
    assert should_update is True
    assert should_recreate is True


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_no_change(task_factory):
    """Test when settings haven't changed"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create execution methods to compare
    old_execution_method = AwsEcsExecutionMethod(task=task)
    task_copy = task
    new_execution_method = AwsEcsExecutionMethod(task=task_copy)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    assert should_update is False
    assert should_recreate is False


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_launch_type_change(task_factory):
    """Test when launch_type changes (should force recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create old execution method
    old_task = task
    old_execution_method = AwsEcsExecutionMethod(task=old_task)
    
    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)
    
    # Modify task settings for new execution method (change launch type)
    new_settings = task_settings.copy()
    new_settings['launch_type'] = 'EC2'  # Change from default FARGATE
    task.execution_method_capability_details = new_settings
    task.save_without_sync()
    
    new_execution_method = AwsEcsExecutionMethod(task=task)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    # Launch type change should force recreate
    assert should_update is True
    assert should_recreate is True


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_platform_version_change(task_factory):
    """Test when platform_version changes (should update but not recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create old execution method
    old_task = task
    old_execution_method = AwsEcsExecutionMethod(task=old_task)
    
    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)
    
    # Modify platform_version
    new_settings = task_settings.copy()
    new_settings['platform_version'] = 'LATEST'  # Change version from 1.4.0
    task.execution_method_capability_details = new_settings
    task.save_without_sync()
    
    new_execution_method = AwsEcsExecutionMethod(task=task)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    # Platform version change should update but not recreate
    assert should_update is True
    assert should_recreate is False


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_task_definition_change(task_factory):
    """Test when task_definition_arn changes (should update but not recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create old execution method
    old_task = task
    old_execution_method = AwsEcsExecutionMethod(task=old_task)
    
    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)
    
    # Modify task_definition_arn
    new_settings = task_settings.copy()
    new_settings['task_definition_arn'] = 'arn:aws:ecs:us-east-1:123456789012:task-definition/new:1'
    task.execution_method_capability_details = new_settings
    task.save_without_sync()
    
    new_execution_method = AwsEcsExecutionMethod(task=task)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    # Task definition change should update but not recreate
    assert should_update is True
    assert should_recreate is False


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_propagate_tags_change(task_factory):
    """Test when propagate_tags changes (should update but not recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create old execution method
    old_task = task
    old_execution_method = AwsEcsExecutionMethod(task=old_task)
    
    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)
    
    # Modify propagate_tags
    new_settings = task_settings.copy()
    new_settings['propagate_tags'] = 'TASK_DEFINITION'
    task.execution_method_capability_details = new_settings
    task.save_without_sync()
    
    new_execution_method = AwsEcsExecutionMethod(task=task)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    # Propagate tags change should update but not recreate
    assert should_update is True
    assert should_recreate is False


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_service_instance_count_change(task_factory):
    """Test when service_instance_count changes (should update but not recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create old execution method
    old_task = task
    old_execution_method = AwsEcsExecutionMethod(task=old_task)
    
    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)
    
    # Change service_instance_count
    task.service_instance_count = 3
    task.save_without_sync()
    
    new_execution_method = AwsEcsExecutionMethod(task=task)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    # Instance count change should update but not recreate
    assert should_update is True
    assert should_recreate is False


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_set_capacity_provider_strategy(task_factory):
    """Test when capacity_provider_strategy is set (should force recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create old execution method
    old_task = task
    old_execution_method = AwsEcsExecutionMethod(task=old_task)
    
    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)
    
    # Add capacity_provider_strategy
    new_settings = task_settings.copy()
    new_settings['capacity_provider_strategy'] = [
        {'capacity_provider': 'FARGATE_SPOT', 'weight': 1}
    ]
    task.execution_method_capability_details = new_settings
    task.save_without_sync()
    
    new_execution_method = AwsEcsExecutionMethod(task=task)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    # Setting capacity provider strategy should force recreate (launch type strategy changes)
    assert should_update is True
    assert should_recreate is True


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_unset_capacity_provider_strategy(task_factory):
    """Test when capacity_provider_strategy is unset (should force recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    # Add capacity_provider_strategy to initial settings
    task_settings['capacity_provider_strategy'] = [
        {'capacity_provider': 'FARGATE_SPOT', 'weight': 1}
    ]
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create old execution method
    old_task = task
    old_execution_method = AwsEcsExecutionMethod(task=old_task)
    
    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)
    
    # Remove capacity_provider_strategy
    new_settings = task_settings.copy()
    new_settings['capacity_provider_strategy'] = None
    task.execution_method_capability_details = new_settings
    task.save_without_sync()
    
    new_execution_method = AwsEcsExecutionMethod(task=task)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    # Unsetting capacity provider strategy should force recreate (launch type strategy changes)
    assert should_update is True
    assert should_recreate is True


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_enable_execute_command_change(task_factory):
    """Test when enable_execute_command changes (should update but not recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task_settings['enable_execute_command'] = False
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create old execution method
    old_task = task
    old_execution_method = AwsEcsExecutionMethod(task=old_task)
    
    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)
    
    # Modify enable_execute_command
    new_settings = task_settings.copy()
    new_settings['enable_execute_command'] = True
    task.execution_method_capability_details = new_settings
    task.save_without_sync()
    
    new_execution_method = AwsEcsExecutionMethod(task=task)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    # Enable execute command change should update but not recreate
    assert should_update is True
    assert should_recreate is False


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_enable_ecs_managed_tags_change(task_factory):
    """Test when enable_ecs_managed_tags changes (should update but not recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment
    
    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()
    
    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task_settings['enable_ecs_managed_tags'] = False
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()
    
    # Create old execution method
    old_task = task
    old_execution_method = AwsEcsExecutionMethod(task=old_task)
    
    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)
    
    # Modify enable_ecs_managed_tags
    new_settings = task_settings.copy()
    new_settings['enable_ecs_managed_tags'] = True
    task.execution_method_capability_details = new_settings
    task.save_without_sync()
    
    new_execution_method = AwsEcsExecutionMethod(task=task)
    
    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)
    
    # Enable ECS managed tags change should update but not recreate
    assert should_update is True
    assert should_recreate is False


@pytest.mark.django_db
@mock_aws
def test_should_update_or_force_recreate_service_resource_management_type_change(task_factory):
    """Test when resource_management_type changes (should force recreate)"""
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    run_env = task.run_environment

    aws_settings = setup_aws()
    run_env.aws_settings = aws_settings.model_dump()
    run_env.save()

    aws_ecs_setup = setup_aws_ecs(run_env)
    task_settings = aws_ecs_setup.make_execution_method_settings().model_dump()
    task.execution_method_capability_details = task_settings
    task.service_instance_count = 1
    task.service_provider_type = SERVICE_PROVIDER_AWS_ECS
    task.save()

    assert task.service_settings is not None
    ss = AwsEcsServiceSettings.model_validate(task.service_settings)
    assert ss.service_arn is not None
    assert ss.resource_management_type is None

    # Create old execution method with no resource_management_type
    old_execution_method = AwsEcsExecutionMethod(task=task)

    # Get a fresh task instance from database for new execution method
    task = Task.objects.get(uuid=task.uuid)

    # Change resource_management_type in service_settings
    new_service_settings = task.service_settings.copy()
    new_service_settings['resource_management_type'] = 'ECS'
    task.service_settings = new_service_settings
    task.save_without_sync()

    new_execution_method = AwsEcsExecutionMethod(task=task)

    should_update, should_recreate = new_execution_method.should_update_or_force_recreate_service(
        old_execution_method=old_execution_method)

    # resource_management_type change should force recreate
    assert should_update is True
    assert should_recreate is True