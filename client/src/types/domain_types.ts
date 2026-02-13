import {
  AWS_ECS_LAUNCH_TYPE_FARGATE,
  DEFAULT_NAME,
  EXECUTION_CAPABILITY_MANUAL_START,
  EXECUTION_METHOD_TYPE_AWS_CODEBUILD,
  EXECUTION_METHOD_TYPE_AWS_ECS,
  EXECUTION_METHOD_TYPE_UNKNOWN,
  INFRASTRUCTURE_TYPE_AWS
} from '../utils/constants';

// Event type constants
export const EVENT_TYPE_TASK_EXECUTION_STATUS_CHANGE = 'task_execution_status_change';
export const EVENT_TYPE_WORKFLOW_EXECUTION_STATUS_CHANGE = 'workflow_execution_status_change';
export const EVENT_TYPE_MISSING_HEARTBEAT_DETECTION = 'missing_heartbeat_detection';
export const EVENT_TYPE_MISSING_SCHEDULED_TASK_EXECUTION = 'missing_scheduled_task_execution';
export const EVENT_TYPE_MISSING_SCHEDULED_WORKFLOW_EXECUTION = 'missing_scheduled_workflow_execution';
export const EVENT_TYPE_INSUFFICIENT_SERVICE_INSTANCES = 'insufficient_service_instances';
export const EVENT_TYPE_DELAYED_TASK_EXECUTION_START = 'delayed_task_execution_start';
export const EVENT_TYPE_BASIC = 'basic';

export const EVENT_TYPES = [
  EVENT_TYPE_DELAYED_TASK_EXECUTION_START,
  EVENT_TYPE_INSUFFICIENT_SERVICE_INSTANCES,
  EVENT_TYPE_MISSING_HEARTBEAT_DETECTION,
  EVENT_TYPE_MISSING_SCHEDULED_TASK_EXECUTION,
  EVENT_TYPE_MISSING_SCHEDULED_WORKFLOW_EXECUTION,
  EVENT_TYPE_TASK_EXECUTION_STATUS_CHANGE,
  EVENT_TYPE_WORKFLOW_EXECUTION_STATUS_CHANGE,
];

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

export interface NamelessEntityReference {
  uuid: string;
  url: string;
  dashboard_url?: string;
}

export interface EntityReference extends NamelessEntityReference {
  name: string;
}

export class EntityReferenceImpl implements EntityReference {
  uuid = '';
  url = '';
  dashboard_url = undefined;
  name = '';
}

export function makeEmptyEntityReference(): EntityReference {
  return new EntityReferenceImpl();
}

interface Timestamped {
  created_at: Date;
  updated_at: Date;
}

interface TrackedEntityReference extends EntityReference, Timestamped {
  created_by_group: GroupReference;
  created_by_user?: string;
}

interface Described {
  description: string;
}

export class TrackedEntityReferenceImpl extends EntityReferenceImpl
implements TrackedEntityReference {
  created_at = new Date();
  updated_at = new Date();
  created_by_group = makeEmptyGroupReference();
  created_by_user = '';
}

export function makeEmptyTrackedEntityReference(): TrackedEntityReference {
  return new TrackedEntityReferenceImpl();
}

// Corresponds to the backend SaasToken model
export interface ApiKey extends TrackedEntityReference, Described {
  access_level: number;
  enabled: boolean;
  group: GroupReference;
  key: string;
  run_environment: EntityReference | null;
  user: string;
}

export interface RateLimitTier {
  max_requests_per_period: number | null;
  request_period_seconds: number | null;
  max_severity: number | null;
  request_period_started_at: Date | null;
  request_count_in_period: number | null;
}

// NotificationDeliveryMethod corresponds to the backend NotificationDeliveryMethod model
export interface NotificationDeliveryMethod extends TrackedEntityReference, Described {
  run_environment: EntityReference | null;
  rate_limit_tiers: RateLimitTier[];
  enabled?: boolean;
  delivery_method_type?: string; // 'email' or 'pagerduty'
}

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace NotificationDeliveryMethod {
  export const MAX_RATE_LIMIT_TIERS = 8;
}

export function makeEmptyNotificationDeliveryMethod(): NotificationDeliveryMethod {
  return Object.assign(makeEmptyTrackedEntityReference(), {
    description: '',
    run_environment: null,
    rate_limit_tiers: [
      {
        max_requests_per_period: 5,
        request_period_seconds: 60,
        max_severity: null,
        request_period_started_at: null,
        request_count_in_period: null,
      },
      {
        max_requests_per_period: 30,
        request_period_seconds: 3600,
        max_severity: null,
        request_period_started_at: null,
        request_count_in_period: null,
      },
      {
        max_requests_per_period: 100,
        request_period_seconds: 86400,
        max_severity: null,
        request_period_started_at: null,
        request_count_in_period: null,
      },
    ],
  });
}

// Email-specific delivery method (backend: EmailNotificationDeliveryMethod)
export interface EmailNotificationDeliveryMethod extends NotificationDeliveryMethod {
  email_to_addresses?: string[] | null;
  email_cc_addresses?: string[] | null;
  email_bcc_addresses?: string[] | null;
}

export function makeEmptyEmailNotificationDeliveryMethod(): EmailNotificationDeliveryMethod {
  return Object.assign(makeEmptyNotificationDeliveryMethod(), {
    email_to_addresses: [],
    email_cc_addresses: [],
    email_bcc_addresses: [],
  });
}

// PagerDuty-specific delivery method (backend: PagerDutyNotificationDeliveryMethod)
export interface PagerDutyNotificationDeliveryMethod extends NotificationDeliveryMethod {
  pagerduty_api_key?: string | null;
  pagerduty_event_class_template?: string | null;
  pagerduty_event_component_template?: string | null;
  pagerduty_event_group_template?: string | null;
}

export function makeEmptyPagerDutyNotificationDeliveryMethod(): PagerDutyNotificationDeliveryMethod {
  return Object.assign(makeEmptyNotificationDeliveryMethod(), {
    pagerduty_api_key: null,
    pagerduty_event_class_template: null,
    pagerduty_event_component_template: null,
    pagerduty_event_group_template: null,
  });
}

// NotificationProfile corresponds to the backend NotificationProfile model
export interface NotificationProfile extends TrackedEntityReference, Described {
  enabled: boolean;
  notification_delivery_methods: EntityReference[];
  run_environment: EntityReference | null;
}

export function makeEmptyNotificationProfile(): NotificationProfile {
  return Object.assign(makeEmptyTrackedEntityReference(), {
    enabled: true,
    notification_delivery_methods: [],
    description: '',
    run_environment: null,
  });
}

export class NotificationProfileImpl extends TrackedEntityReferenceImpl
implements NotificationProfile {
  description = '';
  enabled = true;
  notification_delivery_methods = [];
  run_environment = null;
}


export interface AwsLoggingOptions {
  create_group?: string | null;
  datetime_format?: string | null;
  group?: string | null;
  max_buffer_size?: number | null;
  mode?: string | null;
  multiline_pattern?: string | null;
  region?: string | null;
  stream?: string | null;
  stream_infrastructure_website_url?: string | null;
  stream_prefix?: string | null;
}

export interface AwsLoggingSettings {
  driver?: string | null;
  infrastructure_website_url?: string | null;
  options?: AwsLoggingOptions | null;
}

export interface AwsNetworkSettings {
  assign_public_ip?: boolean | null;
  availability_zone?: string | null;
  //networks: null
  region?: string | null;
  security_group_infrastructure_website_urls?: string[] | null;
  security_groups?: string[] | null;
  subnet_infrastructure_website_urls?: string[] | null;
  subnets?: string[] | null;
}

export interface AwsXraySettings {
  context_missing?: string | null;
  trace_id?: string | null;
}

export interface AwsInfrastructureSettings {
  logging?: AwsLoggingSettings | null;
  network?: AwsNetworkSettings | null;
  xray?: AwsXraySettings | null;
  tags?: {
    [propName: string]: string;
  } | null;
}

export interface AwsTags {
  [propName: string]: string;
}

export interface NamedInfrastructureSettings<T> {
  [name: string]: {
    settings: T;
  }
}

export interface LegacyExecutionMethodCapability {
  capabilities: string[];
  type: string;
}

export class LegacyExecutionMethodCapabilityImpl
implements LegacyExecutionMethodCapabilityImpl {
  capabilities = []
  type = EXECUTION_METHOD_TYPE_UNKNOWN;
}

export interface ContainerSettings {
  name?: string | null;
  docker_id?: string | null;
  docker_name?: string | null;
  image_name?: string | null;
  image_id?: string | null;
  labels?: Record<string, string> | null;
  container_arn?: string | null;
}

export interface AwsEcsExecutionMethodCapability {
  launch_type?: string | null;
  supported_launch_types?: string[] | null;
  cluster_arn?: string | null;
  cluster_infrastructure_website_url?: string | null;
  task_definition_arn?: string | null;
  task_definition_infrastructure_website_url?: string | null;
  infrastructure_website_url?: string | null;
  main_container_name?: string | null;
  main_container_cpu_units?: number | null;
  main_container_memory_mb?: number | null;
  monitor_container_name?: string | null;
  execution_role_arn?: string | null;
  execution_role_infrastructure_website_url?: string | null;
  task_role_arn?: string | null;
  task_role_infrastructure_website_url?: string | null;
  platform_version?: string | null;
  enable_ecs_managed_tags?: boolean | null;
  propagate_tags?: boolean | null;
  task_group?: string | null;
  containers?: ContainerSettings[] | null;
}

export interface AwsEcsExecutionMethodSettings extends AwsEcsExecutionMethodCapability {
  task_arn?: string | null;
  task_infrastructure_website_url?: string | null;
}

export interface NamedExecutionMethodSettings<T> {
  [name: string]: {
    settings: T;
    capabilities?: string[];
    infrastructure_name?: string;
  }
}

export interface RunEnvironment extends TrackedEntityReference, Described {
  infrastructure_settings: {
    [INFRASTRUCTURE_TYPE_AWS]?: NamedInfrastructureSettings<AwsInfrastructureSettings>;
    [key: string]: NamedInfrastructureSettings<any> | undefined;
  };
  execution_method_settings: {
    [EXECUTION_METHOD_TYPE_AWS_ECS]?: NamedExecutionMethodSettings<AwsEcsExecutionMethodSettings>;
    [EXECUTION_METHOD_TYPE_AWS_CODEBUILD]?: NamedExecutionMethodSettings<AwsCodeBuildExecutionMethodSettings>;
    [key: string]: NamedExecutionMethodSettings<any> | undefined;
  };
  notification_profiles: EntityReference[];
  [propName: string]: any;
}

export function makeNewRunEnvironment(): RunEnvironment {
  return Object.assign(makeEmptyTrackedEntityReference(), {
    description: '',
    execution_method_settings: {
      [EXECUTION_METHOD_TYPE_AWS_ECS]: {
        [DEFAULT_NAME]: {
          settings: {
            launch_type: AWS_ECS_LAUNCH_TYPE_FARGATE,
            supported_launch_types: [AWS_ECS_LAUNCH_TYPE_FARGATE],
            platform_version: '1.4.0'
          },
          infrastructure_name: DEFAULT_NAME
        }
      }
    },
    infrastructure_settings: {
      [INFRASTRUCTURE_TYPE_AWS]: {
        [DEFAULT_NAME]: {
          settings: {
            network: {
              subnets: [],
              security_groups: [],
              assign_public_ip: false
            }
          }
        }
      }
    },
    notification_profiles: [],
    tags: null,
  });
}

// Corresponds to the Schedulable model in the backend
export interface Executable extends TrackedEntityReference, Described {
  default_max_retries: number;
  enabled: boolean;
  max_age_seconds: number | null;
  max_concurrency: number | null;
  max_postponed_failure_count: number | null;
  max_postponed_missing_execution_count: number | null;
  max_postponed_timeout_count: number | null;
  min_missing_execution_delay_seconds: number | null;
  notification_event_severity_on_success: number | null;
  notification_event_severity_on_failure: number | null;
  notification_event_severity_on_timeout: number | null;
  notification_event_severity_on_missing_execution: number | null;
  notification_event_severity_on_missing_heartbeat: number | null;
  notification_event_severity_on_service_down: number | null;
  notification_profiles: EntityReference[];
  postponed_failure_before_success_seconds: number | null;
  postponed_missing_execution_before_start_seconds: number | null;
  postponed_timeout_before_success_seconds: number | null;
  required_success_count_to_clear_failure: number | null;
  required_success_count_to_clear_timeout: number | null;
  schedule: string;
  scheduled_instance_count: number | null;
}

export interface AwsLoadBalancer {
  target_group_arn: string;
  container_name: string | null;
  container_port: number;
}

export interface ExternalLink extends TrackedEntityReference, Described {
  link_url: string;
  link_url_template: string;
  icon_url: string | null;
  rank: number;
}

export interface AwsEcsServiceDeploymentCircuitBreaker {
  enable: boolean | null;
  rollback_on_failure: boolean | null;
}

export interface AwsEcsServiceDeploymentConfiguration {
  maximum_percent: number | null;
  minimum_healthy_percent: number | null;
  deployment_circuit_breaker: AwsEcsServiceDeploymentCircuitBreaker | null;
}

export interface AwsApplicationLoadBalancer {
  target_group_arn: string | null;
  target_group_infrastructure_website_url: string | null;
  container_name: string | null;
  container_port: number | null;
}

export interface AwsApplicationLoadBalancerSettings {
  health_check_grace_period_seconds: number | null;
  load_balancers: AwsApplicationLoadBalancer[] | null;
}

export interface AwsEcsServiceSettings {
  deployment_configuration: AwsEcsServiceDeploymentConfiguration | null;
  scheduling_strategy: string | null;
  force_new_deployment: boolean | null;
  load_balancer_settings: AwsApplicationLoadBalancerSettings | null;
  enable_ecs_managed_tags: boolean | null;
  propagate_tags: string | null;
  tags: Record<string, string> | null
  service_arn: string | null;
  infrastructure_website_url: string | null;
}

export interface AwsLambdaExecutionMethodCapability {
  runtime_id: string | null;
  function_arn: string | null;
  function_name: string | null;
  function_version: string | null;
  init_type: string | null;
  dotnet_prejit: string | null;
  function_memory_mb: string | null;
  time_zone_name: string | null;
  infrastructure_website_url: string | null;
}

export interface AwsLambdaExecutionMethodSettings extends AwsLambdaExecutionMethodCapability {
  aws_request_id: string | null;
}

export interface AwsCodeBuildExecutionMethodCapability {
  build_arn: string | null;
  build_image: string | null;
  initiator: string | null;
  source_repo_url: string | null;
  source_version: string | null;
  source_version_infrastructure_website_url: string | null;
  environment_type: string | null;
  compute_type: string | null;
  privileged_mode: boolean | null;
  image_pull_credentials_type: string | null;
  kms_key_id: string | null;
  kms_key_infrastructure_website_url: string | null;
  service_role: string | null;
  service_role_infrastructure_website_url: string | null;
  timeout_in_minutes: number | null;
  queued_timeout_in_minutes: number | null;

  /*
  cache: Optional[AwsCodeBuildCache] = None
  artifacts: Optional[AwsCodeBuildArtifact] = None
  secondary_artifacts: Optional[list[AwsCodeBuildArtifact]] = None
  debug_session_enabled: boolean | null; */

  assumed_role_arn: string | null;
  assumed_role_infrastructure_website_url: string | null;

  infrastructure_website_url: string | null;
  project_name: string | null;
}


export interface AwsCodeBuildExecutionMethodSettings extends AwsCodeBuildExecutionMethodCapability {
    build_id: string | null;
    build_number: number | null;
    batch_build_identifier: string | null;
    build_batch_arn: string | null;
    resolved_source_version: string | null;
    start_time: string | null;
    end_time: string | null;
    current_phase: string | null;
    build_status: string | null;
    build_succeeding: boolean | null;
    build_complete: boolean | null;
    public_build_url: string | null;
    /* TODO
    webhook: Optional[AwsCodeBuildWebhookInfo] = None # From proc_wrapper
    file_system_locations: Optional[list[AwsCodeBuildProjectFileSystemLocation]] = None
    cache: Optional[AwsCodeBuildCache] = None
    reports: Optional[list[AwsCodeBuildReport]] = None
    debug_session: Optional[AwsCodeBuildDebugSession] = None */
}

export interface TaskExecutionConfiguration {
  allocated_cpu_units: number | null;
  allocated_memory_mb: number | null;
  infrastructure_settings: object | null;
  infrastructure_type: string;
  other_metadata: any;
  prevent_offline_execution: boolean | null;
  process_command: string | null;
  process_timeout_seconds: number | null;
  process_max_retries: number | null;
  process_retry_delay_seconds: number | null;
  process_termination_grace_period_seconds: number | null;

  api_retry_delay_seconds: number | null;
  api_resume_delay_seconds: number | null;
  api_error_timeout_seconds: number | null;
  api_task_execution_creation_error_timeout_seconds: number | null;
  api_task_execution_creation_conflict_timeout_seconds: number | null;
  api_task_execution_creation_conflict_retry_delay_seconds: number | null;
  api_final_update_timeout_seconds: number | null;
  api_request_timeout_seconds: number | null;
  status_update_interval_seconds: number | null;
  status_update_port: number | null;
  status_update_message_max_bytes: number | null;
  num_log_lines_sent_on_failure: number | null;
  num_log_lines_sent_on_timeout: number | null;
  num_log_lines_sent_on_success: number | null;
  max_log_line_length: number | null;
  merge_stdout_and_stderr_logs: boolean | null;
  ignore_stdout: boolean | null;
  ignore_stderr: boolean | null;
  managed_probability: number | null;
  failure_report_probability: number | null;
  timeout_report_probability: number | null;
}


export interface Task extends Executable, TaskExecutionConfiguration {
  capabilities: string[];
  execution_method_capability_details: object | null;
  execution_method_type: string;
  heartbeat_interval_seconds: number;
  is_service: boolean;
  latest_task_execution: NamelessEntityReference | null;
  links: ExternalLink[];
  log_query: string;
  logs_url: string;
  max_concurrency: number | null;
  max_heartbeat_lateness_before_abandonment_seconds: number | null;
  max_heartbeat_lateness_before_alert_seconds: number | null;
  max_manual_start_delay_before_abandonment_seconds: number | null;
  max_manual_start_delay_before_alert_seconds: number | null;
  min_service_instance_count: number | null;
  passive: boolean;
  project_url: string;
  run_environment: EntityReference;
  scheduling_provider_type: string | null;
  scheduling_settings: object | null;
  service_instance_count: number;
  service_provider_type: string | null;
  service_settings: object | null;
  was_auto_created: boolean;
}

export class TaskImpl extends TrackedEntityReferenceImpl
implements Task {
  api_retry_delay_seconds = null;
  api_resume_delay_seconds = null;
  api_error_timeout_seconds = null;
  api_task_execution_creation_error_timeout_seconds = null;
  api_task_execution_creation_conflict_timeout_seconds = null;
  api_task_execution_creation_conflict_retry_delay_seconds = null;
  api_final_update_timeout_seconds = null;
  api_request_timeout_seconds = null;
  allocated_cpu_units = null;
  allocated_memory_mb = null;
  capabilities = [];
  created_by_group = new GroupReferenceImpl();
  created_by_user = '';
  default_max_retries = 0;
  description = '';
  enabled = true;
  execution_method_capability_details = null;
  execution_method_type = EXECUTION_METHOD_TYPE_UNKNOWN;
  heartbeat_interval_seconds = 0;
  infrastructure_settings = null;
  infrastructure_type = '';
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
  notification_event_severity_on_success = null;
  notification_event_severity_on_failure = null;
  notification_event_severity_on_timeout = null;
  notification_event_severity_on_missing_execution = null;
  notification_event_severity_on_missing_heartbeat = null;
  notification_event_severity_on_service_down = null;
  notification_profiles = [];
  passive = false;
  postponed_failure_before_success_seconds = null;
  postponed_missing_execution_before_start_seconds = null;
  postponed_timeout_before_success_seconds = null;
  prevent_offline_execution = null;
  process_command = null;
  process_timeout_seconds = null;
  process_max_retries = null;
  process_retry_delay_seconds = null;
  process_termination_grace_period_seconds = null;
  project_url = '';
  required_success_count_to_clear_failure = null;
  required_success_count_to_clear_timeout = null;
  run_environment = new EntityReferenceImpl();
  schedule = '';
  scheduled_instance_count = null;
  scheduling_provider_type = null;
  scheduling_settings = null;
  service_instance_count = 0;
  service_provider_type = null;
  service_settings = null;
  status_update_interval_seconds = null;
  status_update_port = null;
  status_update_message_max_bytes = null;
  num_log_lines_sent_on_failure = null;
  num_log_lines_sent_on_timeout = null;
  num_log_lines_sent_on_success = null;
  max_log_line_length = null;
  merge_stdout_and_stderr_logs = null;
  ignore_stdout = null;
  ignore_stderr = null;
  managed_probability = null;
  failure_report_probability = null;
  timeout_report_probability = null;
  was_auto_created = false;

  canManuallyStart(): boolean {
    return ((this.capabilities as string[]).indexOf(EXECUTION_CAPABILITY_MANUAL_START) >= 0);
  }
}

export interface BuildInfo {
  task_execution: NamelessEntityReference | null;
}

export interface DeployInfo {
  task_execution: NamelessEntityReference | null;
}

export interface Execution extends NamelessEntityReference, Timestamped {
  failed_attempts: number;
  finished_at: Date | null;
  kill_started_at: Date | null;
  kill_finished_at: Date;
  kill_error_code: number | null;
  marked_done_at: Date | null;
  run_reason: string;
  started_at: Date;
  status: string;
  stop_reason: string | null;
  timed_out_attempts: number;
}

export interface ExecutionDetails {
  marked_done_by: string | null;
  killed_by: string | null;
  started_by: string | null;
  notification_profiles: EntityReference[];
}

export interface TaskExecution extends Execution, ExecutionDetails, TaskExecutionConfiguration {
  api_base_url: string,
  api_error_timeout_seconds: number | null;
  api_request_timeout_seconds: number | null;
  api_resume_delay_seconds: number | null,
  api_retry_delay_seconds: number | null,
  api_task_execution_creation_conflict_timeout_seconds: number | null;
  api_task_execution_creation_conflict_retry_delay_seconds: number | null;
  api_task_execution_creation_error_timeout_seconds: number | null;
  api_final_update_timeout_seconds: number | null;
  build: BuildInfo | null;
  commit_url: string;
  current_cpu_units: number | null;
  current_memory_mb: number | null;
  debug_log_tail: string | null;
  deploy: DeployInfo | null;
  deployment: string | null;
  embedded_mode: boolean | null;
  environment_variables_overrides: any;
  error_count: number;
  error_details: any;
  error_log_tail: string | null;
  execution_method_details: object | null;
  execution_method_type: string;
  exit_code: number | null;
  expected_count: number | null;
  heartbeat_interval_seconds: number | null;
  hostname: string | null;
  infrastructure_website_url: string;
  is_service: boolean | null;
  last_heartbeat_at: Date | null;
  last_status_message: string | null;
  marked_outdated_at: Date | null;
  max_conflicting_age_seconds: number | null;
  max_cpu_units: number | null;
  max_memory_mb: number | null;
  mean_cpu_units: number | null;
  mean_memory_mb: number | null;
  other_instance_metadata: any;
  other_runtime_metadata: any;
  task: EntityReference;
  task_max_concurrency: number | null;
  task_version_signature: string | null;
  task_version_number: number | null;
  task_version_text: string | null;
  schedule: string | null;
  skipped_count: number;
  success_count: number;
  workflow_task_instance_execution: BaseWorkflowTaskInstanceExecution | null;
  wrapper_log_level: string | null;
  wrapper_version: string;
}

export interface WorkflowTaskInstance extends TrackedEntityReference, Described {
  allocated_cpu_units: number | null;
  allocated_memory_mb: number | null;
  allow_workflow_execution_after_failure: boolean;
  allow_workflow_execution_after_timeout: boolean;
  default_max_retries: number;
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

export interface WorkflowTransition extends TrackedEntityReference, Described {
  custom_expression: string;
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

export interface WorkflowExecutionSummary extends Execution {
  [propName: string]: any;
}

export interface WorkflowExecution extends WorkflowExecutionSummary {
  workflow: EntityReference;
  workflow_task_instance_executions: WorkflowTaskInstanceExecution[];
  workflow_transition_evaluations: WorkflowTransitionEvaluation[];
}

export interface WorkflowSummary extends Executable {
  latest_workflow_execution: WorkflowExecutionSummary | null;
  [propName: string]: any;
}

export interface Workflow extends WorkflowSummary, ExecutionDetails {
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
    killed_by: null,
    marked_done_by: null,
    max_age_seconds: null,
    max_concurrency: null,
    max_postponed_failure_count: null,
    max_postponed_missing_execution_count: null,
    max_postponed_timeout_count: null,
    min_missing_execution_delay_seconds: null,
    notification_event_severity_on_success: null,
    notification_event_severity_on_failure: null,
    notification_event_severity_on_timeout: null,
    notification_event_severity_on_missing_execution: null,
    notification_event_severity_on_missing_heartbeat: null,
    notification_event_severity_on_service_down: null,
    notification_profiles: [],
    postponed_failure_before_success_seconds: null,
    postponed_missing_execution_before_start_seconds: null,
    postponed_timeout_before_success_seconds: null,
    required_success_count_to_clear_failure: null,
    required_success_count_to_clear_timeout: null,
    schedule: '',
    scheduled_instance_count: null,
    started_by: null,
    workflow_task_instances: [],
    workflow_transitions: [],
    latest_workflow_execution: null,
  };
}

export interface Event extends NamelessEntityReference, Timestamped {
  event_at: Date;
  detected_at: Date | null;
  acknowledged_at: Date | null;
  acknowledged_by_user: string | null;
  severity: string;
  event_type: string;
  error_summary: string | null;
  error_details_message: string | null;
  source: string | null;
  details: Record<string, any> | null;
  grouping_key: string | null;
  resolved_at: Date | null;
  resolved_by_user: string | null;
  resolved_event: NamelessEntityReference | null;
  created_by_group: GroupReference | null;
  run_environment: EntityReference | null;
}

// Subclasses corresponding to backend TypedModel subclasses
export interface ExecutionStatusChangeEvent extends Event {
  status?: number | null;
  postponed_until?: Date | null;
  count_with_same_status_after_postponement?: number | null;
  count_with_success_status_after_postponement?: number | null;
  triggered_at?: Date | null;
}

export interface TaskExecutionStatusChangeEvent extends ExecutionStatusChangeEvent {
  task?: EntityReference;
  task_execution?: NamelessEntityReference;
}

export interface WorkflowExecutionStatusChangeEvent extends ExecutionStatusChangeEvent {
  workflow?: EntityReference;
  workflow_execution?: NamelessEntityReference;
}

export interface MissingHeartbeatDetectionEvent extends Event {
  task?: EntityReference;
  task_execution?: NamelessEntityReference;
  last_heartbeat_at?: Date | null;
  expected_heartbeat_at?: Date | null;
  heartbeat_interval_seconds?: number | null;
}

export interface InsufficientServiceTaskExecutionsEvent extends Event {
  task?: EntityReference;
  interval_start_at?: Date | null;
  interval_end_at?: Date | null;
  detected_concurrency?: number | null;
  required_concurrency?: number | null;
}

export interface MissingScheduledTaskExecutionEvent extends Event {
  task?: EntityReference;
  schedule?: string | null;
  expected_execution_at?: Date | null;
}

export interface MissingScheduledWorkflowExecutionEvent extends Event {
  workflow?: EntityReference;
  schedule?: string | null;
  expected_execution_at?: Date | null;
}

export interface DelayedTaskExecutionStartEvent extends Event {
  task?: EntityReference;
  task_execution?: NamelessEntityReference;
  desired_start_at?: Date | null;
  expected_start_by_deadline?: Date | null;
}

export interface BasicEvent extends Event {}

export type AnyEvent =
  | BasicEvent
  | TaskExecutionStatusChangeEvent
  | WorkflowExecutionStatusChangeEvent
  | MissingHeartbeatDetectionEvent
  | InsufficientServiceTaskExecutionsEvent
  | MissingScheduledTaskExecutionEvent
  | MissingScheduledWorkflowExecutionEvent
  | DelayedTaskExecutionStartEvent
  | Event;

export const castEvent = (ev: any): AnyEvent => {
  if (!ev || !ev.event_type) {
    return ev as Event;
  }
  const key = (ev.event_type || '').toString().toLowerCase();

  const casterMap: { [k: string]: (e: any) => AnyEvent } = {
    [EVENT_TYPE_TASK_EXECUTION_STATUS_CHANGE]: (e) => e as TaskExecutionStatusChangeEvent,
    [EVENT_TYPE_WORKFLOW_EXECUTION_STATUS_CHANGE]: (e) => e as WorkflowExecutionStatusChangeEvent,
    [EVENT_TYPE_MISSING_HEARTBEAT_DETECTION]: (e) => e as MissingHeartbeatDetectionEvent,
    [EVENT_TYPE_MISSING_SCHEDULED_TASK_EXECUTION]: (e) => e as MissingScheduledTaskExecutionEvent,
    [EVENT_TYPE_MISSING_SCHEDULED_WORKFLOW_EXECUTION]: (e) => e as MissingScheduledWorkflowExecutionEvent,
    [EVENT_TYPE_INSUFFICIENT_SERVICE_INSTANCES]: (e) => e as InsufficientServiceTaskExecutionsEvent,
    [EVENT_TYPE_DELAYED_TASK_EXECUTION_START]: (e) => e as DelayedTaskExecutionStartEvent,
    [EVENT_TYPE_BASIC]: (e) => e as BasicEvent,
  };

  const caster = casterMap[key];
  if (caster) {
    return caster(ev);
  }

  return ev as Event;
};

// Notification corresponds to the backend Notification model
export interface Notification extends NamelessEntityReference {
  event: NamelessEntityReference;
  notification_profile: EntityReference;
  notification_delivery_method: EntityReference;
  attempted_at: Date | null;
  completed_at: Date | null;
  send_status: string | null;
  send_result: Record<string, any> | null;
  exception_type: string | null;
  exception_message: string | null;
  rate_limit_max_requests_per_period: number | null;
  rate_limit_request_period_seconds: number | null;
  rate_limit_max_severity: number | null;
  rate_limit_tier_index: number | null;
  created_by_group: GroupReference | null;
}
