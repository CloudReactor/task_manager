export default [{
  controls: [{
    name: 'name',
    label: 'Name',
    type: 'text',
    controlId: 'forName',
    placeholder: 'Give this Email Notification profile a name',
  }, {
    name: 'description',
    label: 'Description',
    type: 'text',
    controlId: 'forDescription',
    placeholder: 'Description of this environment',
  }, {
    name: 'integration_key',
    label: 'Integration key',
    type: 'text',
    controlId: 'forIntegrationKey',
    placeholder: 'PagerDuty API key',
  }, {
    name: 'default_event_severity',
    label: '',
    type: 'select',
    controlId: '',
    placeholder: '',
    addOptionsCase: true,
    options: [
      'critical',
      'error',
      'warning',
      'info',
    ]
  }],
}];