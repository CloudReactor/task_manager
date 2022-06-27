from django.db import models

from ..common import UsageLimits

class SubscriptionPlan(models.Model):
    PLAN_FREE_TIER_NAME     = 'free'
    PLAN_FREE_DURATION_DAYS = 365

    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=5000, blank=True)
    duration_days = models.PositiveIntegerField(null=True)
    usd_price = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    max_users = models.PositiveIntegerField(null=True)
    max_api_keys = models.PositiveIntegerField(null=True)
    max_api_credits_per_month = models.BigIntegerField(null=True)
    max_tasks = models.PositiveIntegerField(null=True)
    max_task_execution_concurrency = models.PositiveIntegerField(null=True)
    max_task_execution_history_items = models.PositiveIntegerField(null=True)
    max_workflows = models.PositiveIntegerField(null=True)
    max_workflow_execution_concurrency = models.PositiveIntegerField(null=True)
    max_workflow_task_instances = models.PositiveIntegerField(null=True)
    max_workflow_execution_history_items = models.PositiveIntegerField(null=True)
    max_alerts_per_day = models.PositiveIntegerField(null=True)

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
