export default [{
  controls: [{
    name: 'name',
    label: 'Name',
    type: 'text',
    placeholder: 'Give this Alert Method a name',
  }, {
    name: 'description',
    label: 'Description',
    type: 'text',
    placeholder: 'Description of this Alert Method',
  }, {
    name: 'enabled',
    label: 'Enabled',
    type: 'checkbox',
    controlId: 'forEnabled',
    subText: 'Uncheck to disable alerts from this Alert Method',
  }],
}, {
  title: 'Alert triggers',
  controls: [{
    name: 'notify_on_success',
    label: 'Notify on success',
    type: 'checkbox',
  }, {
    name: 'notify_on_failure',
    label: 'Notify on failure',
    type: 'checkbox',
  }, {
    name: 'notify_on_timeout',
    label: 'Notify on timeout',
    type: 'checkbox',
  }],
}, {
  title: 'Notification severity levels',
  controls: [{
    name: 'method_details.event_severity',
    label: 'Default event severity',
    type: 'select',
    placeholder: '',
    addOptionsCase: true,
    options: [
      'critical',
      'error',
      'warning',
      'info',
    ]
  }, {
    name: 'error_severity_on_missing_execution',
    label: 'Event severity on missing scheduled execution',
    type: 'select',
    placeholder: '',
    addOptionsCase: true,
    options: [
      'critical',
      'error',
      'warning',
      'info',
      'none',
    ]
  }, {
    name: 'error_severity_on_missing_heartbeat',
    label: 'Event severity on missing heartbeat',
    type: 'select',
    placeholder: '',
    addOptionsCase: true,
    options: [
      'critical',
      'error',
      'warning',
      'info',
      'none',
    ]
  }, {
    name: 'error_severity_on_service_down',
    label: 'Event severity when a service is down',
    type: 'select',
    placeholder: '',
    addOptionsCase: true,
    options: [
      'critical',
      'error',
      'warning',
      'info',
      'none',
    ]
  }],
}];