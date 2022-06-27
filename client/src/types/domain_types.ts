import { EXECUTION_CAPABILITY_MANUAL_START, EXECUTION_METHOD_TYPE_UNKNOWN } from '../utils/constants';

export interface EntityReference {
  uuid: string;
  name: string;
  url: string;
  dashboard_url?: string;
}

export class EntityReferenceImpl implements EntityReference {
  uuid = '';
  name = '';
  url = '';
  dashboard_url? = undefined;
}

export function makeEmptyEntityReference(): EntityReference {
  return new EntityReferenceImpl();
}

interface EntityReferenceWithDates extends EntityReference {
  created_at: Date;
  updated_at: Date;
}

export class EntityReferenceWithDatesImpl extends EntityReferenceImpl
implements EntityReferenceWithDates {
  created_at = new Date();
  updated_at = new Date();
}

export function makeEmptyEntityReferenceWithDates(): EntityReferenceWithDates {
  return new EntityReferenceWithDatesImpl();
}

export interface GroupReference {
  id: number;
  name?: string;
}

export class GroupReferenceImpl {
  id = -1;
  name? = '';
}

export function makeEmptyGroupReference(): GroupReference {
  return new GroupReferenceImpl();
}

export interface ApiKey extends EntityReference {
  created_at: Date;
  description: string;
  enabled: boolean;
  group: GroupReference;
  key: string;
  name: string;
  run_environment: EntityReference | null;
  updated_at: Date;
  user: string;
}

export interface EmailNotificationProfile extends EntityReferenceWithDates {
  created_by_group: GroupReference;
  created_by_user?: string;
  bcc_addresses: string[] | null;
  body_template: string;
  cc_addresses: string[] | null;
  description: string;
  run_environment: EntityReference | null;
  subject_template: string;
  to_addresses: string[] | null;
}

export function makeEmptyEmailNotificationProfile(): EmailNotificationProfile {
  return Object.assign(makeEmptyEntityReferenceWithDates(), {
    bcc_addresses: [],
    body_template: '',
    cc_addresses: [],
    created_by_group: makeEmptyGroupReference(),
    created_by_user: '',
    description: '',
    run_environment: null,
    subject_template: '',
    to_addresses: []
  });
}

export interface PagerDutyProfile extends EntityReferenceWithDates {
  created_by_group: GroupReference;
  created_by_user?: string;
  default_event_severity: string;
  default_event_component_template: string;
  default_event_group_template: string;
  default_event_class_template: string;
  description: string;
  integration_key: string;
  run_environment: EntityReference | null;
}

export function makeEmptyPagerDutyProfile(): PagerDutyProfile {
  return Object.assign(makeEmptyEntityReferenceWithDates(), {
    created_by_group: makeEmptyGroupReference(),
    created_by_user: '',
    default_event_severity: 'error',
    default_event_component_template: '',
    default_event_group_template: '',
    default_event_class_template: '',
    description: '',
    integration_key: '',
    run_environment: null,
  });
}

export interface AlertMethod extends EntityReferenceWithDates {
  created_by_group: GroupReference;
  created_by_user?: string;
  description?: string;
  enabled: boolean;
  notify_on_success: boolean;
  notify_on_failure: boolean;
  notify_on_timeout: boolean;
  error_severity_on_missing_execution: string;
  error_severity_on_missing_heartbeat: string;
  error_severity_on_service_down: string;
  method_details: {
    profile: EntityReference;
    event_severity?: string;
    event_component_template?: string;
    event_group_template?: string;
    event_class_template?: string;
    type: string;
  };
  run_environment: EntityReference | null;
}

export function makeNewAlertMethod(): AlertMethod {
  return Object.assign(makeEmptyEntityReferenceWithDates(), {
    created_by_group: makeEmptyGroupReference(),
    created_by_user: '',
    enabled: true,
    notify_on_success: false,
    notify_on_failure: true,
    notify_on_timeout: true,
    error_severity_on_missing_execution: 'error',
    error_severity_on_missing_heartbeat: 'warning',
    error_severity_on_service_down: 'error',
    method_details: {
      profile: makeEmptyEntityReference(),
      event_severity: 'error',
      type: 'email'
    },
    run_environment: null,
    updated_at: new Date()
  })
}

export interface AwsTags {
  [propName: string]: string;
}

export interface ExecutionMethodCapability {
  capabilities: string[];
  type: string;
}

export class ExecutionMethodCapabilityImpl
implements ExecutionMethodCapabilityImpl {
  capabilities = []
  type = EXECUTION_METHOD_TYPE_UNKNOWN;
}

export interface AwsEcsExecutionMethodCapability
extends ExecutionMethodCapability {
  allocated_cpu_units: number | null;
  allocated_memory_mb: number | null;
  default_subnets: string[];
  default_subnet_infrastructure_website_urls?: (string[] | null);
  default_launch_type: string;
  supported_launch_types: string[];
  default_cluster_arn: string;
  default_cluster_infrastructure_website_url?: string | null;
  default_security_groups: string[];
  default_security_group_infrastructure_website_urls?: (string[] | null);
  default_assign_public_ip: boolean;
  default_execution_role: string;
  default_execution_role_infrastructure_website_url?: string | null;
  default_task_role?: string;
  default_task_role_infrastructure_website_url?: string | null;
  default_platform_version: string;
  tags: AwsTags | null;
}

export class AwsEcsExecutionMethodCapabilityImpl
extends ExecutionMethodCapabilityImpl
implements AwsEcsExecutionMethodCapability {
  allocated_cpu_units = 256;
  allocated_memory_mb = 512;
  default_subnets = [];
  default_subnet_infrastructure_website_urls? = null;
  default_launch_type = 'FARGATE';
  supported_launch_types = ['FARGATE'];
  default_cluster_arn = '';
  default_cluster_infrastructure_website_url? = null;
  default_security_groups = [];
  default_security_group_infrastructure_website_urls? = null;
  default_assign_public_ip = false;
  default_execution_role = '';
  default_execution_role_infrastructure_website_url? = null;
  default_task_role?: string;
  default_task_role_infrastructure_website_url?: string | null;
  default_platform_version = '';
  tags = null;
}

export class TaskAwsEcsExecutionMethodCapability
extends AwsEcsExecutionMethodCapabilityImpl {
  service_options: {
    load_balancer_health_check_grace_period_seconds: number | null;
    load_balancers: AwsLoadBalancer[],
    force_new_deployment: boolean | null;
    deploy_enable_circuit_breaker: boolean | null,
    deploy_rollback_on_failure: boolean | null,
    enable_ecs_managed_tags: boolean | null,
    propagate_tags: string | null,
    tags: AwsTags | null,
  } | null = null;
  task_definition_arn = '';
  task_definition_infrastructure_website_url = null;
}

export interface RunEnvironment extends EntityReferenceWithDates {
  created_by_group: GroupReference;
  aws_account_id: string;
  aws_default_region: string;
  aws_events_role_arn: string,
  aws_access_key: string;
  aws_external_id: string;
  aws_workflow_starter_lambda_arn: string;
  aws_workflow_starter_access_key: string;
  default_alert_methods: EntityReference[];
  execution_method_capabilities: ExecutionMethodCapability[];
  tags: AwsTags | null;
  [propName: string]: any;
}

export function makeNewRunEnvironment(): RunEnvironment {
  return Object.assign(makeEmptyEntityReferenceWithDates(), {
    created_by_group: makeEmptyGroupReference(),
    description: '',
    aws_account_id: '',
    aws_default_region: 'us-west-2',
    aws_events_role_arn: '',
    aws_access_key: '',
    aws_external_id: '',
    aws_workflow_starter_lambda_arn: '',
    aws_workflow_starter_access_key: '',
    execution_method_capabilities: [],
    default_alert_methods: [],
    tags: null,
  });
}

export interface Executable {
  default_max_retries: number;
  enabled: boolean;
  max_age_seconds: number | null;
  max_concurrency: number | null;
  max_postponed_failure_count: number | null;
  max_postponed_missing_execution_count: number | null;
  max_postponed_timeout_count: number | null;
  min_missing_execution_delay_seconds: number | null;
  postponed_failure_before_success_seconds: number | null;
  postponed_missing_execution_before_start_seconds: number | null;
  postponed_timeout_before_success_seconds: number | null;
  schedule: string;
  scheduled_instance_count: number | null;
  should_clear_failure_alerts_on_success: boolean;
  should_clear_timeout_alerts_on_success: boolean;
}

export interface AwsLoadBalancer {
  target_group_arn: string;
  container_name: string | null;
  container_port: number;
}

export interface ExternalLink extends EntityReferenceWithDates {
  link_url: string;
  link_url_template: string;
  description: string | null;
  icon_url: string | null;
  rank: number;
}

export interface CurrentServiceInfo {
  type: string,
  service_arn: string;
  service_arn_updated_at: Date | null;
  service_infrastructure_website_url: string | null;
}

export interface Task extends EntityReferenceWithDates, Executable {
  alert_methods: EntityReference[];
  created_by_group: GroupReference;
  created_by_user?: string;
  current_service_info: CurrentServiceInfo | null;
  description: string;
  execution_method_capability: ExecutionMethodCapability;
  heartbeat_interval_seconds: number;
  is_service: boolean;
  latest_task_execution: any;
  links: ExternalLink[];
  log_query: string;
  logs_url: string;
  max_concurrency: number | null;
  max_heartbeat_lateness_before_abandonment_seconds: number | null;
  max_heartbeat_lateness_before_alert_seconds: number | null;
  max_manual_start_delay_before_abandonment_seconds: number | null;
  max_manual_start_delay_before_alert_seconds: number | null;
  min_service_instance_count: number | null;
  other_metadata: any;
  passive: boolean;
  project_url: string;
  run_environment: EntityReference;
  service_instance_count: number;
  was_auto_created: boolean;
}

export class TaskImpl extends EntityReferenceWithDatesImpl
implements Task {
  alert_methods = []
  created_by_group = new GroupReferenceImpl();
  created_by_user = '';
  current_service_info = null;
  default_max_retries = 0;
  description = '';
  enabled = true;
  execution_method_capability: ExecutionMethodCapability =
    new ExecutionMethodCapabilityImpl();
  heartbeat_interval_seconds = 0;
  is_service = false;
  latest_task_execution = null;
  links = [];
  log_query = '';
  logs_url = '';
  max_age_seconds = null;
  max_concurrency = null;
  max_heartbeat_lateness_before_abandonment_seconds = null;
  max_heartbeat_lateness_before_alert_seconds = null;
  max_manual_start_delay_before_abandonment_seconds = null;
  max_manual_start_delay_before_alert_seconds = null;
  max_postponed_failure_count = null;
  max_postponed_missing_execution_count = null;
  max_postponed_timeout_count = null;
  min_missing_execution_delay_seconds = null;
  min_service_instance_count = null;
  other_metadata = null;
  passive = false;
  postponed_failure_before_success_seconds = null;
  postponed_missing_execution_before_start_seconds = null;
  postponed_timeout_before_success_seconds = null;
  project_url = '';
  run_environment = new EntityReferenceImpl();
  schedule = '';
  scheduled_instance_count = null;
  service_instance_count = 0;
  should_clear_failure_alerts_on_success = false;
  should_clear_timeout_alerts_on_success = false;
  was_auto_created = false;

  canManuallyStart(): boolean {
    const emc = this.execution_method_capability;
    return (emc.capabilities.indexOf(EXECUTION_CAPABILITY_MANUAL_START) >= 0);
  }
}

export interface TaskExecution {
  api_base_url: string,
  api_error_timeout_seconds: number | null;
  api_request_timeout_seconds: number | null;
  api_resume_delay_seconds: number | null,
  api_retry_delay_seconds: number | null,
  api_task_execution_creation_conflict_timeout_seconds: number | null;
  api_task_execution_creation_conflict_retry_delay_seconds: number | null;
  api_task_execution_creation_error_timeout_seconds: number | null;
  api_final_update_timeout_seconds: number | null;
  commit_url: string;
  created_at: Date;
  current_cpu_units: number | null;
  current_memory_mb: number | null;
  dashboard_url: string;
  debug_log_tail: string | null;
  deployment: string | null;
  embedded_mode: boolean | null;
  environment_variables_overrides: any;
  error_count: number;
  error_log_tail: string | null;
  execution_method: {
    allocated_cpu_units: number;
    allocated_memory_mb: number;
    assign_public_ip: boolean | null;
    cluster_arn: string;
    cluster_infrastructure_website_url: string | null;
    execution_role: string;
    execution_role_infrastructure_website_url: string | null;
    launch_type: string;
    platform_version: string;
    security_groups: string[];
    security_group_infrastructure_website_urls: (string | null)[] | null;
    subnets: string[];
    subnet_infrastructure_website_urls: (string | null)[] | null;
    tags: AwsTags | null;
    task_arn: string;
    task_definition_arn: string;
    task_definition_infrastructure_website_url: string | null;
    task_role: string | null;
    task_role_infrastructure_website_url: string | null;
    type: string;
  };
  exit_code: number | null;
  expected_count: number | null;
  failed_attempts: number;
  finished_at: Date | null;
  heartbeat_interval_seconds: number | null;
  hostname: string | null;
  infrastructure_website_url: string;
  is_service: boolean | null;
  killed_by: string,
  kill_error_code: number;
  kill_finished_at: number;
  kill_started_at: number;
  last_heartbeat_at: Date | null;
  last_status_message: string | null;
  marked_done_at: Date | null;
  marked_outdated_at: Date | null;
  max_conflicting_age_seconds: number | null;
  max_cpu_units: number | null;
  max_memory_mb: number | null;
  mean_cpu_units: number | null;
  mean_memory_mb: number | null;
  other_instance_metadata: any;
  other_runtime_metadata: any;
  prevent_offline_execution: boolean | null;
  process_command: string | null,
  process_max_retries: number | null;
  task: EntityReference;
  task_max_concurrency: number | null;
  process_retry_delay_seconds: number | null;
  process_termination_grace_period_seconds: number | null;
  process_timeout_seconds: number | null;
  task_version_signature: string | null;
  task_version_number: number | null;
  task_version_text: string | null;
  schedule: string | null;
  skipped_count: number;
  started_at: Date;
  started_by: string;
  status: string;
  status_update_interval_seconds: number | null,
  status_update_message_max_bytes: number | null,
  status_update_port: number | null,
  stop_reason: string | null;
  success_count: number;
  timed_out_attempts: number;
  updated_at: Date;
  url: string;
  uuid: string;
  workflow_task_instance_execution: BaseWorkflowTaskInstanceExecution | null;
  wrapper_log_level: string | null;
  wrapper_version: string;
}

export interface WorkflowTaskInstance extends EntityReferenceWithDates {
  allocated_cpu_units: number | null;
  allocated_memory_mb: number | null;
  allow_workflow_execution_after_failure: boolean;
  allow_workflow_execution_after_timeout: boolean;
  default_max_retries: number;
  description: string;
  environment_variables_overrides: object | null;
  failure_behavior: string;
  max_age_seconds: number | null;

  // For compatibility with old snapshots
  process_type?: EntityReference;

  task?: EntityReference;
  timeout_behavior: string;
  ui_center_margin_left: number | null;
  ui_center_margin_top: number | null;
  ui_color: string;
  ui_icon_type: string;
  ui_scale: number | null;
  workflow: EntityReference;
  start_transition_condition: string;
  [propName: string]: any;
}

export interface WorkflowTransition extends EntityReferenceWithDates {
  custom_expression: string;
  description: string;
  exit_codes: number[];

  from_workflow_task_instance?: EntityReference;

  // For compatibility with old snapshots
  from_workflow_process_type_instance?: EntityReference;

  priority: number | null;
  rule_type: string,
  threshold_property: string | null;

  to_workflow_task_instance?: EntityReference;

  // For compatibility with old snapshots
  to_workflow_process_type_instance?: EntityReference;

  ui_color: string;
  ui_line_style: string;
  ui_scale: number | null;
  [propName: string]: any;
}

export interface BaseWorkflowTaskInstanceExecution {
  uuid: string;
  workflow_task_instance: EntityReference;
  workflow_execution: EntityReference;
  is_latest: boolean;
  created_at: Date;
}

export interface WorkflowTaskInstanceExecution
  extends BaseWorkflowTaskInstanceExecution {
  task_execution: TaskExecution;
}

export interface WorkflowTransitionEvaluation {
  evaluated_at: Date;
  result: boolean;
  uuid: string;
  workflow_transition: EntityReference;
  workflow_execution: EntityReference;
}

export interface WorkflowExecutionSummary {
  created_at: Date;
  dashboard_url: string;
  failed_attempts: number;
  finished_at: Date;
  kill_started_at: Date;
  kill_finished_at: Date;
  kill_error_code: number;
  marked_done_at: Date;
  run_reason: string;
  started_at: Date;
  status: string;
  stop_reason: string,
  timed_out_attempts: number;
  updated_at: Date;
  url: string;
  uuid: string;
  [propName: string]: any;
}

export interface WorkflowExecution extends WorkflowExecutionSummary {
  started_by: string;
  killed_by: string;
  marked_done_by: string;
  workflow: EntityReference;
  workflow_task_instance_executions: WorkflowTaskInstanceExecution[];
  workflow_transition_evaluations: WorkflowTransitionEvaluation[];
}

export interface WorkflowSummary extends EntityReferenceWithDates,
    Executable {
  created_at: Date;
  created_by_group: GroupReference;
  created_by_user?: string;
  description: string;
  latest_workflow_execution: WorkflowExecutionSummary | null;
  [propName: string]: any;
}

export interface Workflow extends WorkflowSummary {
  alert_methods: EntityReference[];

  workflow_task_instances?: WorkflowTaskInstance[];

  // For compatibility with old snapshots
  workflow_process_type_instances?: WorkflowTaskInstance[];

  workflow_transitions: WorkflowTransition[];
}

export function makeNewWorkflow(): Workflow {
  return {
    uuid: '',
    name: 'Workflow 1',
    url: '',
    created_at: new Date(),
    updated_at: new Date(),
    created_by_group: makeEmptyGroupReference(),
    created_by_user: '',
    default_max_retries: 0,
    description: '',
    enabled: true,
    max_age_seconds: null,
    max_concurrency: null,
    max_postponed_failure_count: null,
    max_postponed_missing_execution_count: null,
    max_postponed_timeout_count: null,
    min_missing_execution_delay_seconds: null,
    postponed_failure_before_success_seconds: null,
    postponed_missing_execution_before_start_seconds: null,
    postponed_timeout_before_success_seconds: null,
    schedule: '',
    scheduled_instance_count: null,
    should_clear_failure_alerts_on_success: false,
    should_clear_timeout_alerts_on_success: false,
    workflow_task_instances: [],
    workflow_transitions: [],
    latest_workflow_execution: null,
    alert_methods: []
  };
}
