import factory
from faker import Factory as FakerFactory

from processes.models import WorkflowTaskInstance

from .task_factory import TaskFactory
from .workflow_factory import WorkflowFactory

faker = FakerFactory.create()


class WorkflowTaskInstanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkflowTaskInstance

    name = factory.Sequence(lambda n: f'wti_{n}')
    description = ''
    workflow = factory.SubFactory(WorkflowFactory)
    task = factory.SubFactory(TaskFactory)
    start_transition_condition = WorkflowTaskInstance.START_TRANSITION_CONDITION_ANY
    max_complete_executions = 1
    should_eval_transitions_after_first_execution = False
    condition_count_threshold = None
    condition_ratio_threshold = None
    max_age_seconds = None
    default_max_retries = 0
    environment_variables_overrides = None
    allocated_cpu_units = None
    allocated_memory_mb = None
    use_task_notification_profiles = False
    failure_behavior = WorkflowTaskInstance.FAILURE_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED
    allow_workflow_execution_after_failure = False
    timeout_behavior = WorkflowTaskInstance.TIMEOUT_BEHAVIOR_TIMEOUT_WORKFLOW_IF_UNHANDLED
    allow_workflow_execution_after_timeout = False

    ui_color = ''
    ui_center_margin_top = 0
    ui_center_margin_left = 0
    ui_icon_type = ''
    ui_scale = 1.0
