from processes.execution_methods import UnknownExecutionMethod

from .task_factory import TaskFactory

class UnknownExecutionMethodTaskFactory(TaskFactory):
    log_query = ''
    was_auto_created = True
    passive = True

    execution_method_type = UnknownExecutionMethod.NAME

    aws_ecs_task_definition_arn = ''
    aws_ecs_default_launch_type = ''
    aws_ecs_supported_launch_types = None

    allocated_cpu_units = None
    allocated_memory_mb = None
