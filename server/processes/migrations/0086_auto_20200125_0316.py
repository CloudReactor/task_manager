# Generated by Django 2.2.2 on 2020-01-25 03:16

from typing import Any

from django.db import migrations


def copy_aws_ecs_load_balancers(apps, schema_editor):
    # FIXME: We shouldn't reference current code's models in a migration
    Task = apps.get_model('processes', 'Task')
    AwsEcsServiceLoadBalancerDetails = apps.get_model('processes', 'AwsEcsServiceLoadBalancerDetails')

    for task in Task.objects.exclude(aws_ecs_service_load_balancer_target_group_arn__exact=''):
        AwsEcsServiceLoadBalancerDetails(
            process_type=task,
            target_group_arn=task.aws_ecs_service_load_balancer_target_group_arn,
            container_name=task.aws_ecs_service_load_balancer_container_name,
            container_port=task.aws_ecs_service_load_balancer_container_port
        ).save()

class Migration(migrations.Migration):
    dependencies = [
        ('processes', '0085_awsecsserviceloadbalancerdetails'),
    ]

    operations: list[Any] = [
        # Comment out to start from scratch
        # migrations.RunPython(copy_aws_ecs_load_balancers),
    ]
