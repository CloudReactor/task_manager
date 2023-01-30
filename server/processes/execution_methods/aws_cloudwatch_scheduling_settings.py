from typing import Optional

from pydantic import BaseModel

SCHEDULING_TYPE_AWS_CLOUDWATCH = 'AWS CloudWatch'


class AwsCloudwatchSchedulingSettings(BaseModel):
    execution_rule_name: Optional[str] = None
    event_rule_arn: Optional[str] = None
    event_target_rule_name: Optional[str] = None
    event_target_id: Optional[str] = None
    event_bus_name: Optional[str] = None
