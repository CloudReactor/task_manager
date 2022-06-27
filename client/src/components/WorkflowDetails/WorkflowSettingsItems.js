export default [{
  controls: [{
    name: 'description',
    label: 'Description',
    type: 'text',
    controlId: 'forDescription',
    placeholder: '',
    subText: 'Enter a description for the Workflow (optional).',
  }, {
    name: 'max_concurrency',
    label: 'Max Concurrency',
    type: 'number',
    controlId: 'forMaxConcurrency',
    min: '1',
    subText: 'Enter the maximum number of concurrent executions of the Workflow. Leave blank to allow unlimited concurrency.',
  }, {
    name: 'max_age_seconds',
    label: 'Timeout (seconds)',
    type: 'number',
    controlId: 'forMaxTimeout',
    min: '1',
    subText: 'Enter the maximum duration, in seconds, the Workflow is allowed to run for. Leave blank to allow the Workflow to run for an unlimited duration.',
  }, {
    name: 'enabled',
    label: 'Enabled',
    type: 'checkbox',
    controlId: 'forEnabled',
    subText: 'Uncheck to disable running this Workflow at its scheduled time.',
  }],
}];