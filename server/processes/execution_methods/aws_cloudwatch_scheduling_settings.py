

from ..common import PydanticSettingsModel

SCHEDULING_TYPE_AWS_CLOUDWATCH = 'AWS CloudWatch'


class AwsCloudwatchSchedulingSettings(PydanticSettingsModel):
    execution_rule_name: str | None = None
    event_rule_arn: str | None = None
    event_target_rule_name: str | None = None
    event_target_id: str | None = None
    event_bus_name: str | None = None
