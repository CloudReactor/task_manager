from typing import Optional

from dataclasses import dataclass


def add_limits(x: Optional[int], y: Optional[int]) -> Optional[int]:
    if (x is None) or (y is None):
        return None

    return x + y


@dataclass
class UsageLimits:
    max_users: Optional[int] = None
    max_api_keys: Optional[int] = None
    max_api_credits_per_month: Optional[int] = None
    max_tasks: Optional[int] = None
    max_task_execution_concurrency: Optional[int] = None
    max_task_execution_history_items: Optional[int] = None
    max_workflows: Optional[int] = None
    max_workflow_execution_concurrency: Optional[int] = None
    max_workflow_task_instances: Optional[int] = None
    max_workflow_execution_history_items: Optional[int] = None
    max_alerts_per_day: Optional[int] = None
    max_events: Optional[int] = None
    max_notifications: Optional[int] = None

    def combine(self, other: 'UsageLimits') -> 'UsageLimits':
        return UsageLimits(
                max_users=add_limits(self.max_users, other.max_users),
                max_api_keys=add_limits(self.max_api_keys, other.max_api_keys),
                max_api_credits_per_month=add_limits(self.max_api_credits_per_month, other.max_api_credits_per_month),
                max_tasks=add_limits(self.max_tasks, other.max_tasks),
                max_task_execution_concurrency=add_limits(self.max_task_execution_concurrency, other.max_task_execution_concurrency),
                max_task_execution_history_items=add_limits(self.max_task_execution_history_items, other.max_task_execution_history_items),
                max_workflows=add_limits(self.max_workflows, other.max_workflows),
                max_workflow_execution_concurrency=add_limits(self.max_workflow_execution_concurrency, other.max_workflow_execution_concurrency),
                max_workflow_task_instances=add_limits(self.max_workflow_task_instances, other.max_workflow_task_instances),
                max_workflow_execution_history_items=add_limits(self.max_workflow_execution_history_items, other.max_workflow_execution_history_items),
                max_alerts_per_day=add_limits(self.max_alerts_per_day, other.max_alerts_per_day),
                max_events=add_limits(self.max_events, other.max_events),
                max_notifications=add_limits(self.max_notifications, other.max_notifications),
        )

    @staticmethod
    def default_limits() -> 'UsageLimits':
        return UsageLimits(
                max_users=50,
                max_api_keys=25,
                max_api_credits_per_month=10000,
                max_tasks=2000,
                max_task_execution_concurrency=4,
                max_task_execution_history_items=1000,
                max_workflows=100,
                max_workflow_execution_concurrency=1,
                max_workflow_task_instances=200,
                max_workflow_execution_history_items=1000,
                max_alerts_per_day=1000,
                max_events=20000,
                max_notifications=20000,
        )
