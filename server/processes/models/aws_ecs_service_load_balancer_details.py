import logging

from django.db import models

from .task import Task


logger = logging.getLogger(__name__)


class AwsEcsServiceLoadBalancerDetails(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE,
        related_name='aws_ecs_service_load_balancer_details_set',
        db_column='process_type_id')
    target_group_arn = models.CharField(max_length=1000)
    container_name = models.CharField(max_length=1000, blank=True)
    container_port = models.IntegerField()
