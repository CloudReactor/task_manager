from dynamic_fixtures.fixtures import BaseFixture

from processes.models import SubscriptionPlan


class Fixture(BaseFixture):
    def load(self):
        SubscriptionPlan.objects.update_or_create(name='Enterprise', defaults={
            'description': 'Enterprise Plan',
            'duration_days': 365,
            'max_users': 100,
            'max_api_keys': 500,
            'max_api_credits_per_month': 1000000,
            'max_tasks': 2000,
            'max_task_execution_concurrency': 50,
            'max_task_execution_history_items': 5000,
            'max_workflows': 1000,
            'max_workflow_execution_concurrency': 10,
            'max_workflow_task_instances': 200,
            'max_workflow_execution_history_items': 5000,
            'max_alerts_per_day': 5000,
        })
