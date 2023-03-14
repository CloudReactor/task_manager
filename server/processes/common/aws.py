from typing import Optional

import logging
import re

from urllib.parse import quote, quote_plus


from rest_framework.exceptions import APIException

AWS_ECS_PLATFORM_VERSION_LATEST = 'LATEST'

HTTPS = 'https://'
AWS_CONSOLE_HOSTNAME = 'console.aws.amazon.com'
AWS_CONSOLE_BASE_URL = HTTPS + AWS_CONSOLE_HOSTNAME + '/'

VPC_HOME_PATH = 'vpc/home'
ECS_HOME_PATH = 'ecs/home'

logger = logging.getLogger(__name__)

def handle_aws_multiple_failure_response(response) -> None:
    """
    Handle response with this structure:
    {
        'FailedEntryCount': 123,
        'FailedEntries': [
            {
                'TargetId': 'string',
                'ErrorCode': 'string',
                'ErrorMessage': 'string'
            },
        ]
    }
    """
    if response['FailedEntryCount'] > 0:
        message = "Failed to put_targets():\n"
        for entry in response['FailedEntries']:
            message += f"Error code {entry['ErrorCode']}: {entry['ErrorMessage']}\n"

        raise APIException(detail=message)

def make_regioned_aws_console_base_url(region: str) -> str:
    return HTTPS + region + '.' + AWS_CONSOLE_HOSTNAME + '/'

def make_region_parameter(region: str) -> str:
    return 'region=' + quote(region)

def make_aws_console_role_url(role_arn: Optional[str]) -> Optional[str]:
    if not role_arn:
        return None

    try:
        last_slash_index = role_arn.rindex('/')
        return AWS_CONSOLE_BASE_URL + 'iam/home#/roles/' + quote(role_arn[last_slash_index+1:])
    except Exception:
        logger.error(f'Failed to compute AWS role URL for ARN {role_arn}',
                exc_info=True)
        return None

def make_aws_console_subnet_url(subnet_name: Optional[str],
        region: Optional[str]) -> Optional[str]:
    if not subnet_name or not region:
        return None

    return make_regioned_aws_console_base_url(region) + VPC_HOME_PATH + \
            '?' + make_region_parameter(region) + '#SubnetDetails:subnetId=' + \
            quote(subnet_name)

def make_aws_console_security_group_url(security_group_name: Optional[str],
        region: Optional[str]) -> Optional[str]:
    if not security_group_name or not region:
        return None

    return make_regioned_aws_console_base_url(region) + VPC_HOME_PATH + \
            '?' + make_region_parameter(region) + '#SecurityGroup:groupId=' + \
            quote(security_group_name)

def extract_cluster_name(ecs_cluster_arn: Optional[str]) -> Optional[str]:
    if not ecs_cluster_arn:
        return None

    try:
        last_slash_index = ecs_cluster_arn.rindex('/')
        return ecs_cluster_arn[last_slash_index+1:]
    except Exception:
        logger.error(f'Failed to compute cluster name for ARN {ecs_cluster_arn}',
                exc_info=True)
        return None


def make_aws_console_ecs_cluster_url(ecs_cluster_arn: Optional[str]) -> Optional[str]:
    if not ecs_cluster_arn:
        return None

    cluster_name = extract_cluster_name(ecs_cluster_arn)

    if not cluster_name:
        logger.error(f'Failed to compute AWS console URL for ARN {ecs_cluster_arn}: no cluster name',
                exc_info=True)
        return None

    try:
        parts = ecs_cluster_arn.split(':')
        region = parts[3]
        return make_regioned_aws_console_base_url(region) + ECS_HOME_PATH + \
                '?' + make_region_parameter(region) + '#/clusters/' + quote(cluster_name) + \
                '/tasks'
    except Exception:
        logger.error(f'Failed to compute AWS console URL for ARN {ecs_cluster_arn}',
                exc_info=True)

    return None

def make_aws_console_ecs_task_definition_url(task_definition_arn: Optional[str]) -> Optional[str]:
    if not task_definition_arn:
        return None

    try:
        parts = task_definition_arn.split(':')
        region = parts[3]
        version_number = parts[-1]
        middle = parts[-2]
        slash_index = middle.index('/')
        task_name = middle[slash_index+1:]

        return make_regioned_aws_console_base_url(region) + ECS_HOME_PATH + \
                '?' + make_region_parameter(region) + '#/taskDefinitions/' + quote(task_name) + \
                '/' + version_number
    except Exception:
        logger.error(f'Failed to compute AWS console URL for ARN {task_definition_arn}',
                exc_info=True)

    return None

def make_aws_console_ecs_service_url(ecs_service_arn: Optional[str],
        cluster_name: Optional[str] = None):
    if not ecs_service_arn:
        return None

    # ECS Service ARN has old format:
    # arn:aws:ecs:[region]:[aws_account_id]:service/[service_name]

    # ECS Service ARN has new format:
    # arn:aws:ecs:[region]:[aws_account_id]:service/[cluster_name]/[service_name]

    # AWS Console URL has format:
    # https://us-east-2.console.aws.amazon.com/ecs/home?region=us-east-2#/clusters/[cluster_name]/services/[service_name]/details

    try:
        parts = ecs_service_arn.split(':')
        region = parts[3]
        last_part = parts[5]

        last_part_parts = last_part.split('/')
        if len(last_part_parts) < 3:
            if not cluster_name:
                logger.info('Service ARN is old format and no cluster name given, returning None')
                return None
            service_name = last_part_parts[1]
        else:
            cluster_name = last_part_parts[1]
            service_name = last_part_parts[2]

        return make_regioned_aws_console_base_url(region) + ECS_HOME_PATH \
                + '?' + make_region_parameter(region) + '#/clusters/' \
                + quote(cluster_name) + '/services/' \
                + quote(service_name) + '/details'
    except Exception:
        logger.error(f'Failed to compute AWS console URL for ECS Service ARN {ecs_service_arn}',
                exc_info=True)

    return None

def make_aws_console_lambda_function_url(
        function_arn: Optional[str]) -> Optional[str]:
    if function_arn is None:
        return None

    # function_arn format:
    # arn:aws:lambda:<region>:<aws account id>:function:<function name>
    tokens = function_arn.split(':')

    if (len(tokens) < 7) or (tokens[0] != 'arn') or \
        (tokens[1] != 'aws') or (tokens[2] != 'lambda') or \
        (tokens[5] != 'function'):
        logger.warning(f"AWS Lambda Execution Method: function_arn is not the expected format")
        return None

    region = tokens[3]
    function_name_in_arn = tokens[6]

    return f"https://{region}.console.aws.amazon.com/lambda/home?" + \
        make_region_parameter(region) + "#/functions/" + \
        function_name_in_arn


def aws_encode(value: str):
      """
      From rh0dium on
      https://stackoverflow.com/questions/60796991/is-there-a-way-to-generate-the-aws-console-urls-for-cloudwatch-log-group-filters

      """
      value = quote_plus(value)
      value = re.sub(r"\+", " ", value)
      return re.sub(r"%", "$", quote_plus(value))
