export default [{
  title: 'AWS ECS Settings',
  controls: [{
    name: 'execution_method_capabilities[0].default_cluster_arn',
    label: 'Default Cluster',
    type: 'text',
    controlId: 'forExecutionMethodCapabilitiesDefaultClusterArn',
    placeholder: 'staging',
    subText: 'The name or ARN of the default ECS cluster used to run Tasks',
  }, {
    name: 'execution_method_capabilities[0].default_execution_role',
    label: 'Task Execution Role',
    type: 'text',
    controlId: 'forExecutionMethodCapabilitiesDefaultExecutionRole',
    placeholder: 'arn:aws:iam::123456789012:role/staging-taskExecutionRole-XXX',
    subText: 'The name or ARN of a role that is used to start ECS tasks, which should be assumable by the CloudReactor Role'
  }, {
    name: 'execution_method_capabilities[0].default_task_role',
    label: 'Default Task Role',
    type: 'text',
    controlId: 'forExecutionMethodCapabilitiesDefaultTaskRole',
    placeholder: 'arn:aws:iam::123456789012:role/staging-taskRole-XXX',
    subText: 'Optional. The name or ARN of a role that gives Tasks running in this Run Environment access to other AWS resources.',
  }, {
    name: 'execution_method_capabilities[0].default_platform_version',
    label: 'Default Platform Version',
    type: 'select',
    controlId: 'forExecutionMethodCapabilitiesDefaultPlatformVersion',
    placeholder: '1.4.0',
    options: [
      '1.3.0',
      '1.4.0',
      'LATEST',
    ],
    subText: 'Optional. Specifies the ECS platform version. Defaults to LATEST.',
  }, {
    name: 'execution_method_capabilities[0].default_assign_public_ip',
    label: 'Assign Public IP by Default',
    type: 'checkbox',
    controlId: 'forExecutionMethodCapabilitiesDefaultAssignPublicIp',
    subText: 'Check if your Tasks should be given a public IP when executed. This should be checked if you run your Tasks in a public subnet.',
  }],
}];