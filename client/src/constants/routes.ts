export const LOGIN = '/login';
export const REGISTER = '/signup';
export const REGISTRATION_PENDING = '/signup_pending';
export const REGISTRATION_ACTIVATION = '/activate_user';
export const PASSWORD_RESET = '/password_reset';
export const DASHBOARD = '/';
export const TASKS = '/tasks';
export const TASK = '/tasks/:uuid';
export const TASK_EXECUTIONS = '/task_executions';
export const TASK_EXECUTION = '/task_executions/:uuid';
export const WORKFLOWS = '/workflows';
export const WORKFLOW = '/workflows/:uuid';
export const WORKFLOW_EXECUTION = '/workflow_executions/:uuid';
export const RUN_ENVIRONMENTS = '/run_environments';
export const RUN_ENVIRONMENT = '/run_environments/:uuid';
export const GROUPS = '/groups';
export const GROUP = '/groups/:id';

// Legacy routes
export const NOTIFICATION_METHODS = '/legacy_notification_methods';
export const NOTIFICATION_METHOD = '/legacy_notification_methods/:uuid';
export const PAGERDUTY_PROFILES = '/legacy_pagerduty_profiles';
export const PAGERDUTY_PROFILE = '/legacy_pagerduty_profiles/:uuid'
export const EMAIL_NOTIFICATION_PROFILES = '/legacy_email_notification_profiles';
export const EMAIL_NOTIFICATION_PROFILE = '/legacy_email_notification_profiles/:uuid';

export const NOTIFICATION_PROFILES = '/notification_profiles'
export const NOTIFICATION_PROFILE = '/notification_profiles/:uuid'
export const NOTIFICATION_DELIVERY_METHODS = '/notification_delivery_methods'
export const NOTIFICATION_DELIVERY_METHOD = '/notification_delivery_methods/:uuid'
export const API_KEYS = '/api_keys'
export const API_KEY = '/api_keys/:uuid'
export const PROFILE = '/profile'
