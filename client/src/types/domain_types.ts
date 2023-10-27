import {
  AWS_ECS_LAUNCH_TYPE_FARGATE,
  DEFAULT_NAME,
  EXECUTION_CAPABILITY_MANUAL_START,
  EXECUTION_METHOD_TYPE_UNKNOWN,
  INFRASTRUCTURE_TYPE_AWS
} from '../utils/constants';

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

export interface AwsEcsExecutionMethodCapability {
  launch_type?: string | null;
  supported_launch_types?: string[] | null;
  cluster_arn?: string | null;
  cluster_infrastructure_website_url?: string | null;
  task_definition_arn?: string | null;
  task_definition_infrastructure_website_url?: string | null;
  infrastructure_website_url?: string | null;
  main_container_name?: string | null;
  execution_role_arn?: string | null;
  execution_role_infrastructure_website_url?: string | null;
  task_role_arn?: string | null;
  task_role_infrastructure_website_url?: string | null;
  platform_version?: string | null;
  enable_ecs_managed_tags?: boolean | null;
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

export interface RunEnvironment extends EntityReferenceWithDates {
  created_by_group: GroupReference;
  infrastructure_settings: {
    [INFRASTRUCTURE_TYPE_AWS]?: NamedInfrastructureSettings<AwsInfrastructureSettings>;
    [key: string]: NamedInfrastructureSettings<any> | undefined;
  };
  execution_method_settings: {
    'AWS ECS'?: NamedExecutionMethodSettings<AwsEcsExecutionMethodSettings>;
    [key: string]: NamedExecutionMethodSettings<any> | undefined;
  };
  default_alert_methods: EntityReference[];
  [propName: string]: any;
}

export function makeNewRunEnvironment(): RunEnvironment {
  return Object.assign(makeEmptyEntityReferenceWithDates(), {
    created_by_group: makeEmptyGroupReference(),
    description: '',
    execution_method_settings: {
      [INFRASTRUCTURE_TYPE_AWS]: {
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
  environment_type: string | null;
  compute_type: string | null;
  privileged_mode: boolean | null;
  image_pull_credentials_type: string | null;
  kms_key_id: string | null;
  service_role: string | null;
  timeout_in_minutes: number | null;
  queued_timeout_in_minutes: number | null;

  /*
  cache: Optional[AwsCodeBuildCache] = None
  artifacts: Optional[AwsCodeBuildArtifact] = None
  secondary_artifacts: Optional[list[AwsCodeBuildArtifact]] = None
  debug_session_enabled: boolean | null; */

  infrastructure_website_url: string | null;
  project_name: string | null;
}


export interface AwsCodeBuildExecutionMethodSettings extends AwsCodeBuildExecutionMethodCapability {
    build_id: string | null;
    build_number: number | null;
    batch_build_identifier: string | null;
    build_batch_arn: string | null;
    source_version: string | null;
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


export interface Task extends EntityReferenceWithDates, Executable {
  alert_methods: EntityReference[];
  allocated_cpu_units: number | null;
  allocated_memory_mb: number | null;
  capabilities: string[];
  created_by_group: GroupReference;
  created_by_user?: string;
  description: string;
  execution_method_capability_details: object | null;
  execution_method_type: string;
  heartbeat_interval_seconds: number;
  infrastructure_settings: object | null;
  infrastructure_type: string;
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
  scheduling_provider_type: string | null;
  scheduling_settings: object | null;
  service_instance_count: number;
  service_provider_type: string | null;
  service_settings: object | null;
  was_auto_created: boolean;
}

export class TaskImpl extends EntityReferenceWithDatesImpl
implements Task {
  alert_methods = [];
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
  passive = false;
  postponed_failure_before_success_seconds = null;
  postponed_missing_execution_before_start_seconds = null;
  postponed_timeout_before_success_seconds = null;
  project_url = '';
  run_environment = new EntityReferenceImpl();
  schedule = '';
  scheduled_instance_count = null;
  scheduling_provider_type = null;
  scheduling_settings = null;
  service_instance_count = 0;
  service_provider_type = null;
  service_settings = null;
  should_clear_failure_alerts_on_success = false;
  should_clear_timeout_alerts_on_success = false;
  was_auto_created = false;

  canManuallyStart(): boolean {
    return ((this.capabilities as string[]).indexOf(EXECUTION_CAPABILITY_MANUAL_START) >= 0);
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
  allocated_cpu_units: number | null;
  allocated_memory_mb: number | null;
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
  // Deprecated
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
  execution_method_details: object | null;
  execution_method_type: string;
  exit_code: number | null;
  expected_count: number | null;
  failed_attempts: number;
  finished_at: Date | null;
  heartbeat_interval_seconds: number | null;
  hostname: string | null;
  infrastructure_type: string | null;
  infrastructure_settings: object | null;
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
