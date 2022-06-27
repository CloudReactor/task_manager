from dataclasses import dataclass

@dataclass
class UsageLimits:
    max_users: int = 0
    max_api_keys: int = 0
    max_api_credits_per_month: int = 0
    max_tasks: int = 0
    max_task_execution_concurrency: int = 0
    max_task_execution_history_items: int = 0
    max_workflows: int = 0
    max_workflow_execution_concurrency: int = 0
    max_workflow_task_instances: int = 0
    max_workflow_execution_history_items: int = 0
    max_alerts_per_day: int = 0

    def combine(self, other: 'UsageLimits') -> 'UsageLimits':
        return UsageLimits(
                max_users=self.max_users + other.max_users,
                max_api_keys=self.max_api_keys + other.max_api_keys,
                max_api_credits_per_month=self.max_api_credits_per_month + other.max_api_credits_per_month,
                max_tasks=self.max_tasks + other.max_tasks,
                max_task_execution_concurrency=self.max_task_execution_concurrency + other.max_task_execution_concurrency,
                max_task_execution_history_items=self.max_task_execution_history_items + other.max_task_execution_history_items,
                max_workflows=self.max_workflows + other.max_workflows,
                max_workflow_execution_concurrency=self.max_workflow_execution_concurrency + other.max_workflow_execution_concurrency,
                max_workflow_task_instances=self.max_workflow_task_instances + other.max_workflow_task_instances,
                max_workflow_execution_history_items=self.max_workflow_execution_history_items + other.max_workflow_execution_history_items,
                max_alerts_per_day=self.max_alerts_per_day + other.max_alerts_per_day,
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
        )
