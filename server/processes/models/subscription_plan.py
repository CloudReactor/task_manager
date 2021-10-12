from django.db import models

from ..common import UsageLimits

class SubscriptionPlan(models.Model):
    PLAN_FREE_TIER_NAME     = 'free'
    PLAN_FREE_DURATION_DAYS = 365

    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=5000, blank=True)
    duration_days = models.IntegerField()
    usd_price = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    max_users = models.IntegerField()
    max_api_keys = models.IntegerField()
    max_api_credits_per_month = models.BigIntegerField()
    max_tasks = models.IntegerField()
    max_task_execution_concurrency = models.IntegerField()
    max_task_execution_history_items = models.IntegerField()
    max_workflows = models.IntegerField()
    max_workflow_execution_concurrency = models.IntegerField()
    max_workflow_task_instances = models.IntegerField()
    max_workflow_execution_history_items = models.IntegerField()
    max_alerts_per_day = models.IntegerField()

    @property
    def usage_limits(self) -> UsageLimits:
        return UsageLimits(
                max_users=self.max_users,
                max_api_keys=self.max_api_keys,
                max_api_credits_per_month=self.max_api_credits_per_month,
                max_tasks=self.max_tasks,
                max_task_execution_concurrency=self.max_task_execution_concurrency,
                max_task_execution_history_items=self.max_task_execution_history_items,
                max_workflows=self.max_workflows,
                max_workflow_execution_concurrency=self.max_workflow_execution_concurrency,
                max_workflow_task_instances=self.max_workflow_task_instances,
                max_workflow_execution_history_items=self.max_workflow_execution_history_items,
                max_alerts_per_day=self.max_alerts_per_day,
        )


    def __str__(self):
        return self.name
