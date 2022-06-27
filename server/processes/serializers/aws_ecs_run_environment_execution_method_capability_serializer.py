from processes.serializers.base_execution_method_capability_serializer import BaseExecutionMethodCapabilitySerializer

from ..models.run_environment import RunEnvironment

from ..execution_methods import ExecutionMethod

from .base_aws_ecs_execution_method_serializer import (
    BaseAwsEcsExecutionMethodSerializer
)

class AwsEcsRunEnvironmentExecutionMethodCapabilitySerializer(
        BaseAwsEcsExecutionMethodSerializer,
        BaseExecutionMethodCapabilitySerializer):

    def get_capabilities(self, run_env: RunEnvironment) -> list[str]:
        if run_env.can_control_aws_ecs():
            return [c.name for c in ExecutionMethod.ALL_CAPABILITIES]
        return []
