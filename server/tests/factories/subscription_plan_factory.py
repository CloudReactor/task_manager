from processes.models import SubscriptionPlan

import factory
from faker import Factory as FakerFactory

from pytest_factoryboy import register

faker = FakerFactory.create()


@register
class SubscriptionPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SubscriptionPlan

    name = factory.Sequence(lambda n: f'plan_{n}')
    description = 'Some Plan!'
    duration_days = 366
    usd_price = 100.0
    max_users = 100
    max_api_keys = 100
    max_api_credits_per_month = 100000
    max_tasks = 100
    max_task_execution_concurrency = 100
    max_task_execution_history_items = 100
    max_workflows = 100
    max_workflow_execution_concurrency = 100
    max_workflow_task_instances = 100
    max_workflow_execution_history_items = 100
    max_alerts_per_day = 100
