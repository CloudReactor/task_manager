from typing import Optional

import logging
import re

from urllib.parse import quote, quote_plus


from rest_framework.exceptions import APIException

AWS_ECS_PLATFORM_VERSION_LATEST = 'LATEST'

HTTPS = 'https://'
AWS_CONSOLE_HOSTNAME = 'console.aws.amazon.com'
AWS_CONSOLE_BASE_URL = HTTPS + AWS_CONSOLE_HOSTNAME + '/'

S3_ARN_PREFIX = 'arn:aws:s3:::'
S3_ARN_PREFIX_LENGTH = len(S3_ARN_PREFIX)

VPC_HOME_PATH = 'vpc/home'
ECS_HOME_PATH = 'ecs/home'

KMS_ARN_REGEX = re.compile(r'^arn:aws:kms:([^:]+):(\d+):(.+)')


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

def normalize_role_arn(role_arn_or_name, aws_account_id: Optional[str], region: Optional[str]) -> str:
    if aws_account_id and region:
        if role_arn_or_name.startswith('arn:'):

            return role_arn_or_name
        else:
            return 'arn:aws:iam::' + aws_account_id + ':role/' + role_arn_or_name

    return role_arn_or_name


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

def make_aws_console_s3_object_url(object_arn: str) -> Optional[str]:
    # Example object ARN: arn:aws:s3:::bucket/pipeline/App/OGgJCVJ.zip
    # Example output URL: https://s3.console.aws.amazon.com/s3/object/bucket?prefix=pipeline/App/OGgJCVJ.zip

    if object_arn.startswith(S3_ARN_PREFIX):
        try:
            first_slash_index = object_arn.index('/')
            bucket_name = object_arn[S3_ARN_PREFIX_LENGTH:first_slash_index]
            object_name = object_arn[(first_slash_index + 1):]

            return "https://s3.console.aws.amazon.com/s3/object/" + quote(bucket_name) + \
                    '?prefix=' + quote(object_name)
        except Exception:
            logger.error(f'Failed to compute AWS console URL for S3 object {object_arn}',
                    exc_info=True)
    else:
        logger.warning(f"S3 ARN {object_arn=} is not the expected format")

    return None

def make_aws_console_kms_key_url(key_id: str, region: Optional[str] = None) -> Optional[str]:
    # Example key ID: xyz-deadbeefdeadbeefdeadbeefdeadbeef
    # Example output URL: https://us-west-1.console.aws.amazon.com/kms/home?region=us-west-1#/kms/keys/xyz-deadbeefdeadbeefdeadbeefdeadbeef

    resolved_key_id = key_id

    m = KMS_ARN_REGEX.match(key_id)

    if m:
        path = m.group(3)

        if path.startswith('key/'):
            resolved_key_id = path[len('key/'):]
        else:
            # Can't lookup a key by alias in the AWS console
            return None

        region_in_arn = m.group(1)

        if region and (region != region_in_arn):
            logger.warning(f"Region {region=} in ARN {key_id=} does not match region {region=} passed in")

        region = region_in_arn

    if not region:
        return None

    return make_regioned_aws_console_base_url(region) + 'kms/home?' + \
        make_region_parameter(region) + '#/kms/keys/' + aws_encode(resolved_key_id)


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
                logger.warning('Service ARN is old format and no cluster name given, returning None')
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
        logger.warning(f"AWS Lambda Execution Method: {function_arn=} is not the expected format")
        return None

    region = tokens[3]
    function_name_in_arn = tokens[6]

    return f"https://{region}.console.aws.amazon.com/lambda/home?" + \
        make_region_parameter(region) + "#/functions/" + \
        function_name_in_arn


def make_aws_console_codebuild_build_url(
        build_arn: Optional[str]) -> Optional[str]:
    if build_arn is None:
        return None

    # build_arn format:
    # arn:aws:codebuild:<region>:<aws account id>:build/<project>[:build_id]
    tokens = build_arn.split(':')
    token_len = len(tokens)

    if (token_len < 6) or (token_len > 7) or (tokens[0] != 'arn') or \
        (tokens[1] != 'aws') or (tokens[2] != 'codebuild') or \
        (not tokens[5].startswith('build/')):
        logger.warning(f"AWS CodeBuild Execution Method: {build_arn=} is not the expected format")
        return None

    region = tokens[3]
    account_id = tokens[4]
    project = tokens[5][len('build/'):]

    build_id: Optional[str] = None
    if token_len == 7:
        build_id = tokens[6]

    url = f"https://{region}.console.aws.amazon.com/codesuite/codebuild/{account_id}/projects/" + \
            quote_plus(project)

    if build_id:
        url += ("/build/" + quote_plus(project) + "%3A" + build_id)
    else:
        url += "/history"

    return url + "?" + make_region_parameter(region)


def aws_encode(value: str):
    """
    From rh0dium on
    https://stackoverflow.com/questions/60796991/is-there-a-way-to-generate-the-aws-console-urls-for-cloudwatch-log-group-filters

    """
    value = quote_plus(value)
    value = re.sub(r"\+", " ", value)
    return re.sub(r"%", "$", quote_plus(value))


def make_flattened_environment(env: dict[str, str]) -> list[dict[str, str]]:
    flattened = []
    for name, value in env.items():
        flattened.append({
            'name': name,
            'value': value
        })

    return flattened
