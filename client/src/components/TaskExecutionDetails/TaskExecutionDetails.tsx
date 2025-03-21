import {
  RunEnvironment,
  Task,
  TaskExecution,
  AwsEcsExecutionMethodSettings,
  AwsLambdaExecutionMethodSettings,
  AwsCodeBuildExecutionMethodSettings,
  AwsInfrastructureSettings
} from '../../types/domain_types';

import {
  formatBoolean, formatNumber,
  timeDuration, timeFormat,
  formatDuration,
  makeLink, makeLinks
} from "../../utils/index";

import React, { Fragment } from 'react';

import { Col, Row, Table } from 'react-bootstrap';
import {
  EXECUTION_METHOD_TYPE_AWS_CODEBUILD,
  EXECUTION_METHOD_TYPE_AWS_ECS,
  EXECUTION_METHOD_TYPE_AWS_LAMBDA,
  INFRASTRUCTURE_TYPE_AWS
} from '../../utils/constants';

import styles from './TaskExecutionDetails.module.scss';

interface Props {
  taskExecution: TaskExecution;
  task: Task | null;
  runEnvironment: RunEnvironment | null;
}

interface NameValuePair {
  name: string;
  value: any;
}

function pair(name: string, value: any) {
  return { name, value: value ?? 'N/A' };
}

function formatTime(x: Date | null) : string {
  return timeFormat(x, true);
}

function makeLogSection(te: TaskExecution, isStdout: boolean) {
  const logLines = isStdout ? te.debug_log_tail : te.error_log_tail;
  return (
    <Row className="my-2">
      <Col>
        <h5 className="my-3">{isStdout ? 'Debug log' : 'Error log'}:</h5>
        {
          (logLines === null) ? <div>N/A</div> : (
            <textarea className={styles.logBlock}
            rows={10} readOnly={true} value={logLines} />
          )
        }
      </Col>
    </Row>
  );
}

const TaskExecutionDetails = ({ taskExecution, task, runEnvironment }: Props) => {
  const te = taskExecution;
  const tem = te.execution_method_details;
  let rows = [
    pair('Status', te.status),
    pair('Started by', te.started_by),
    pair('Started at', formatTime(te.started_at)),
    pair('Finished at', formatTime(te.finished_at)),
    pair('Duration', timeDuration(te.started_at, te.finished_at)),
    pair('Last heartbeat at', formatTime(te.last_heartbeat_at)),
    pair('Heartbeat interval', formatDuration(te.heartbeat_interval_seconds)),
    pair('Version signature', makeLink(te.task_version_signature, te.commit_url)),
    pair('Version number', te.task_version_number),
    pair('Version text', te.task_version_text),
    pair('Deployment', te.deployment),
    pair('Command', te.process_command),
    pair('Allocated CPU units', formatNumber(te.allocated_cpu_units)),
    pair('Allocated memory (MB)', formatNumber(te.allocated_memory_mb)),
    pair('Other instance metadata', te.other_instance_metadata ?
      JSON.stringify(te.other_instance_metadata) : 'None'),
    pair('Exit code', te.exit_code),
    pair('Stop reason', te.stop_reason),
    pair('Stopped by', te.killed_by),
    pair('Error details', te.error_details ? JSON.stringify(te.error_details) : 'None'),
    pair('Last status message', te.last_status_message),
    pair('Success count', formatNumber(te.success_count)),
    pair('Skipped count', formatNumber(te.skipped_count)),
    pair('Error count', formatNumber(te.error_count)),
    pair('Expected count', formatNumber(te.expected_count)),
    pair('Failed attempts', formatNumber(te.failed_attempts)),
    pair('Timed out attempts', formatNumber(te.timed_out_attempts)),
    pair('Hostname', te.hostname),
    pair('Wrapper version', te.wrapper_version),
    pair('Embedded mode', formatBoolean(te.embedded_mode)),
    pair('Run as service?', formatBoolean(te.is_service)),
    pair('Max concurrency', formatNumber(te.task_max_concurrency)),
    pair('Max conflicting age', formatDuration(te.max_conflicting_age_seconds)),
    pair('Prevent offline execution', formatBoolean(te.prevent_offline_execution)),
    pair('Max Task retries', formatNumber(te.process_max_retries)),
    pair('Termination grace period', formatDuration(te.process_termination_grace_period_seconds)),
    pair('API error timeout', formatDuration(te.api_error_timeout_seconds)),
    pair('API retry delay', formatDuration(te.api_retry_delay_seconds)),
    pair('API resume delay', formatDuration(te.api_resume_delay_seconds)),
    pair('API Task Execution creation conflict timeout',
      formatDuration(te.api_task_execution_creation_conflict_timeout_seconds)),
    pair('API Task Execution creation error timeout',
      formatDuration(te.api_task_execution_creation_error_timeout_seconds)),
    pair('API Task Execution creation retry delay',
      formatDuration(te.api_task_execution_creation_conflict_retry_delay_seconds)),
    pair('API final update timeout',
      formatDuration(te.api_final_update_timeout_seconds)),
    pair('API request timeout', formatDuration(te.api_request_timeout_seconds)),
    pair('Status update port', te.status_update_port ?? 'N/A'),
    pair('Status message max bytes', formatNumber(te.status_update_message_max_bytes)),
    pair('Wrapper log level', te.wrapper_log_level),
    pair('Log lines sent on failure', formatNumber(te.num_log_lines_sent_on_failure)),
    pair('Log lines sent on timeout', formatNumber(te.num_log_lines_sent_on_timeout)),
    pair('Log lines sent on success', formatNumber(te.num_log_lines_sent_on_success)),
    pair('Max log line length',  formatNumber(te.max_log_line_length)),
    pair('Merge stdout and stderr logs', formatBoolean(te.merge_stdout_and_stderr_logs)),
    pair('Ignore stdout', formatBoolean(te.ignore_stdout)),
    pair('Ignore stderr', formatBoolean(te.ignore_stderr)),
    pair('API base URL', te.api_base_url),
    pair('Build Task Execution', te.build?.task_execution ?
      makeLink(te.build.task_execution.uuid,
        '/task_executions/' + te.build.task_execution.uuid, true) : 'N/A'),
    pair('Deployment Task Execution', te.deploy?.task_execution ?
      makeLink(te.deploy.task_execution.uuid,
        '/task_executions/' + te.deploy.task_execution.uuid, true) : 'N/A'),
    pair('Execution method', te.execution_method_type)
  ];

  if (tem) {
    switch (te.execution_method_type) {
      case EXECUTION_METHOD_TYPE_AWS_ECS: {
        const awsEcsTem = tem as AwsEcsExecutionMethodSettings;
        rows = rows.concat([
          pair('ECS launch type', awsEcsTem.launch_type),
          pair('ECS cluster', makeLink(awsEcsTem.cluster_arn, awsEcsTem.cluster_infrastructure_website_url)),
          pair('ECS task definition ARN', makeLink(awsEcsTem.task_definition_arn,
            awsEcsTem.task_definition_infrastructure_website_url)),
          pair('ECS task ARN', makeLink(awsEcsTem.task_arn, awsEcsTem.infrastructure_website_url)),
          pair('ECS task role ARN', makeLink(awsEcsTem.task_role_arn,
            awsEcsTem.task_role_infrastructure_website_url)),
          pair('ECS platform version', awsEcsTem.platform_version),
        ]);
      }
      break;

      case EXECUTION_METHOD_TYPE_AWS_LAMBDA: {
        const awsLambdaTem = tem as AwsLambdaExecutionMethodSettings;
        rows = rows.concat([
          pair('Function version', awsLambdaTem.function_version),
          pair('AWS Request ID', awsLambdaTem.aws_request_id),

        ]);
      }
      break;

      case EXECUTION_METHOD_TYPE_AWS_CODEBUILD: {
        const awsCbTem = tem as AwsCodeBuildExecutionMethodSettings;
        rows = rows.concat([
          pair('Build ARN', makeLink(awsCbTem.build_arn, awsCbTem.infrastructure_website_url)),
          pair('Build ID', makeLink(awsCbTem.build_id, awsCbTem.infrastructure_website_url)),
          pair('Build number', awsCbTem.build_number),
          pair('Source version', makeLink(awsCbTem.source_version,
            awsCbTem.source_version_infrastructure_website_url)),
          pair('Resolved source version', awsCbTem.resolved_source_version),
          pair('Build started at', awsCbTem.start_time),
          pair('Build ended at', awsCbTem.end_time),
          pair('Build status', awsCbTem.build_status),
          pair('Current phase', awsCbTem.current_phase),
          pair('Build succeeding?', formatBoolean(awsCbTem.build_succeeding)),
          pair('Build complete?', formatBoolean(awsCbTem.build_complete)),
          pair('Initiator', awsCbTem.initiator),
          pair('Batch build ID', awsCbTem.batch_build_identifier),
          pair('Batch build ARN', awsCbTem.build_batch_arn),
          pair('Public build URL', makeLink(awsCbTem.public_build_url, awsCbTem.public_build_url)),
          pair('Assumed role ARN', awsCbTem.assumed_role_arn ?
            makeLink(awsCbTem.assumed_role_arn, awsCbTem.assumed_role_infrastructure_website_url)
            : 'N/A'),
        ]);
      }
      break;

      default:
      break;
    };
  }

  rows.push(pair('Infrastructure provider', te.infrastructure_type));

  const teInfra = taskExecution.infrastructure_settings;
  const taskInfra = task?.infrastructure_settings;
  const runEnvInfra = runEnvironment?.infrastructure_settings;
  if (teInfra || taskInfra || runEnvInfra) {
    let infraRows: NameValuePair[] = [];

    switch (te.infrastructure_type) {
      case INFRASTRUCTURE_TYPE_AWS: {
          const awsSettings = teInfra as AwsInfrastructureSettings | undefined;
          const taskAwsSettings = taskInfra as AwsInfrastructureSettings | undefined;
          const runEnvAwsSettings = runEnvInfra ? (runEnvInfra[INFRASTRUCTURE_TYPE_AWS]?.["__default__"]?.settings as AwsInfrastructureSettings | undefined)
            : undefined;
          const awsNetworkSettings = awsSettings?.network;
          const taskAwsNetworkSettings = taskAwsSettings?.network;
          const runEnvAwsNetworkSettings = runEnvAwsSettings?.network;

          if (awsNetworkSettings || taskAwsNetworkSettings || runEnvAwsNetworkSettings) {
            infraRows = infraRows.concat([
              pair('Networking', ''),
              pair('Region', awsNetworkSettings?.region ??
                (taskAwsNetworkSettings?.region ?
                  `Task default (${taskAwsNetworkSettings.region})` :
                  (runEnvAwsNetworkSettings?.region ?
                    `Run Environment default (${runEnvAwsNetworkSettings.region})` :
                    'N/A')
                )
              ),
              pair('Subnets', (awsNetworkSettings?.subnets && Array.isArray(awsNetworkSettings.subnets)) ?
                makeLinks(awsNetworkSettings.subnets,
                  awsNetworkSettings?.subnet_infrastructure_website_urls) : (
                    (taskAwsNetworkSettings?.subnets && Array.isArray(taskAwsNetworkSettings.subnets)) ?
                    <span>Task Default ({
                      makeLinks(taskAwsNetworkSettings.subnets,
                        taskAwsNetworkSettings?.subnet_infrastructure_website_urls)
                    })</span> : <span>Run Environment default ({
                      makeLinks(runEnvAwsNetworkSettings?.subnets ?? [],
                        runEnvAwsNetworkSettings?.subnet_infrastructure_website_urls)
                    })</span>

                  )),
              pair('Security groups', (awsNetworkSettings?.security_groups && Array.isArray(awsNetworkSettings.security_groups)) ?
                makeLinks(awsNetworkSettings.security_groups,
                  awsNetworkSettings.security_group_infrastructure_website_urls) : (
                    (taskAwsNetworkSettings?.security_groups && Array.isArray(taskAwsNetworkSettings.security_groups)) ?
                    <span>Task default ({
                      makeLinks(taskAwsNetworkSettings.security_groups,
                        taskAwsNetworkSettings.security_group_infrastructure_website_urls)
                    })</span> : <span>Run Environment default ({
                      makeLinks(runEnvAwsNetworkSettings?.security_groups ?? [],
                        runEnvAwsNetworkSettings?.security_group_infrastructure_website_urls)
                    })</span>
                )),
              pair('Assign public IP?', formatBoolean(awsNetworkSettings?.assign_public_ip ??
                taskAwsNetworkSettings?.assign_public_ip ?? runEnvAwsNetworkSettings?.assign_public_ip ??
                false)),
            ]);
          }

          const awsLogging = awsSettings?.logging;

          if (awsLogging) {
            infraRows = infraRows.concat([
              pair('Logging', ''),
              pair('Log Driver', awsLogging.driver)
            ]);

            const loggingOptions = awsLogging.options;

            if (loggingOptions?.group || awsLogging.infrastructure_website_url) {
              infraRows.push(pair('Log Group',
                makeLink(loggingOptions?.group ?? 'View',
                  awsLogging.infrastructure_website_url)));
            }

            if (loggingOptions) {
              infraRows = infraRows.concat([
                pair('Stream Prefix', loggingOptions.stream_prefix),
                pair('Stream',
                  makeLink(loggingOptions.stream,
                    loggingOptions.stream_infrastructure_website_url))
              ]);
            }
          }

          const tags = awsSettings?.tags;

          if (tags) {
            infraRows.push(pair('Tags', ''));
            for (const [k, v] of Object.entries(tags)) {
              infraRows.push(pair(k, v));
            }
          } else {
            infraRows.push(pair('Tags', '(None)'));
          }

          const xray = awsSettings?.xray;

          if (xray) {
            infraRows.push(pair('X-Ray', ''));
            infraRows.push(pair('Trace ID', xray.trace_id));
          }
        }
      break;

      default:
      break;
    }

    rows = rows.concat(infraRows);
  }

/*
    pair('ECS execution role', makeLink(awsEcsTem.execution_role,
      awsEcsTem.execution_role_infrastructure_website_url)),
    pair('Subnet(s) ', makeLinks(awsEcsTem.subnets, awsEcsTem.subnet_infrastructure_website_urls)),
    pair('Security group(s) ', makeLinks(awsEcsTem.security_groups, awsEcsTem.security_group_infrastructure_website_urls)),
    pair('Assign public IP', (awsEcsTem.assign_public_ip === null) ? 'Unknown' :
      (awsEcsTem.assign_public_ip ? 'ENABLED' : 'DISABLED')),
  */

  rows = rows.concat([
     pair('Workflow Execution',
      makeLink(te?.workflow_task_instance_execution?.workflow_execution?.uuid,
        '/workflow_executions/' +
        te?.workflow_task_instance_execution?.workflow_execution?.uuid)),
  ]);

  /*,
  pair('PagerDuty notified at ', pe.pagerduty_event_sent_at, true),
  pair('PagerDuty event severity ', pe.pagerduty_event_severity), */

	return (
    <Fragment>
      <Table striped bordered responsive hover size="sm">
        <tbody>
          {rows.map(row => (
            <tr key={row.name}>
              <td style={{fontWeight: 'bold'}}>
                {row.name}
              </td>
              <td align="left">{row.value}</td>
            </tr>
          ))}
        </tbody>
      </Table>
      { makeLogSection(te, true) }
      { makeLogSection(te, false) }
    </Fragment>
	);
}

export default TaskExecutionDetails;
