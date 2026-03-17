import pytest

from moto import mock_aws

from processes.execution_methods.aws_cloudwatch_scheduling_settings import (
    SCHEDULING_TYPE_AWS_CLOUDWATCH,
    AwsCloudwatchSchedulingSettings
)
from processes.execution_methods.aws_ecs_execution_method import AwsEcsExecutionMethod
from processes.models import Task

@pytest.mark.django_db
@mock_aws
def test_aws_ecs_scheduled_task_execution_setup_and_teardown(task_factory):
    task = task_factory(execution_method_type=AwsEcsExecutionMethod.NAME)
    task.save()                      

    assert task.enabled is True
    assert task.scheduling_settings is None

    task.schedule = 'rate(5 minutes)'
    task.schedule_provider = SCHEDULING_TYPE_AWS_CLOUDWATCH
    task.scheduled_instance_count = 1
    task.save()

    assert task.schedule_provider == SCHEDULING_TYPE_AWS_CLOUDWATCH
    assert task.scheduled_instance_count == 1
    assert task.schedule_updated_at is not None
    
    ss_dict = task.scheduling_settings

    assert ss_dict is not None
    ss = AwsCloudwatchSchedulingSettings.model_validate(ss_dict)

    assert ss.event_rule_arn is not None
    assert ss.event_target_id is not None
    assert ss.event_target_rule_name is not None

    




