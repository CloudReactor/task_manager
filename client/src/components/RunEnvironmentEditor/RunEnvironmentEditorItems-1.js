export default [{
  title: 'AWS General Settings',
  controls: [{
    name: 'aws_account_id',
    label: 'AWS Account ID',
    type: 'text',
    controlId: 'forAwsAccountId',
    placeholder: '123456789012',
  }, {
    name: 'aws_default_region',
    label: 'AWS default region',
    type: 'select',
    controlId: '',
    placeholder: '',
    options: [
      'us-east-1',
      'us-east-2',
      'us-west-1',
      'us-west-2',
      'us-gov-east-1',
      'us-gov-west-1',
      'ap-west-1',
      'ap-south-1',
      'ap-northeast-1',
      'ap-northeast-2',
      'ap-northeast-3',
      'eu-central-1',
      'eu-west-1',
      'eu-west-2',
      'eu-west-3',
      'eu-north-1',
      'me-south-1',
      'sa-east-1',
      'ca-central-1',
      'cn-north-1',
      'cn-northwest-1'
    ]
  }],
},{
  title: 'CloudReactor Access',
  controls: [{
    name: 'aws_events_role_arn',
    label: 'Cloudreactor Role',
    type: 'text',
    controlId: 'forAwsEventsRoleArn',
    placeholder: 'arn:aws:iam::123456789012:role/CloudReactor-staging-executionSchedulingRole-XXX',
    subText: 'The name or ARN of a role that is assumable by CloudReactor, giving it permission to manage your Tasks'
  }, {
    name: 'aws_assumed_role_external_id',
    label: 'External ID',
    type: 'text',
    controlId: 'forAwsAssumedRoleExternalId',
    placeholder: 'SomeKey',
    subText: 'A secret value that is used to authenticate management requests are from CloudReactor.'
  }, {
    name: 'aws_workflow_starter_lambda_arn',
    label: 'Workflow Starter Lambda',
    type: 'text',
    controlId: 'forAwsWorkflowStarterLambdaArn',
    placeholder: 'arn:aws:lambda:us-west-2:123456789012:function:CloudReactor-staging-workflowStarterLambda-XXX',
    subText: 'The name or ARN of the Lambda function, installed by the CloudReactor role CloudFormation template, that starts Workflows'
  }, {
    name: 'aws_workflow_starter_access_key',
    label: 'Workflow Starter Access Key',
    type: 'text',
    controlId: 'forAwsWorkflowStarterAccessKey',
    placeholder: 'SomeKey',
    subText: 'A secret value that is used to authenticate requests to start Workflows are from CloudReactor.'
  }],
}];
