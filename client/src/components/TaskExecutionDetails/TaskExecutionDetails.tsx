import { TaskExecution } from '../../types/domain_types';
import {
  formatBoolean, formatNumber,
  timeDuration, timeFormat,
  formatDuration,
  makeLink, makeLinks
} from "../../utils/index";

import React from 'react';

import { Table } from 'react-bootstrap';
import { EXECUTION_METHOD_TYPE_AWS_ECS } from '../../utils/constants';

interface Props {
  taskExecution: TaskExecution
}

function pair(name: string, value: any) {
  return { name, value: value ?? 'N/A' };
}

function formatTime(x: Date | null) : string {
  return timeFormat(x, true);
}

const TaskExecutionDetails = ({ taskExecution }: Props) => {
  const te = taskExecution;
  const tem = te.execution_method
  let rows = [
    pair('Status', te.status),
    pair('Started by', te.started_by),
    pair('Started at', formatTime(te.started_at)),
    pair('Finished at', formatTime(te.finished_at)),
    pair('Duration', timeDuration(te.started_at, te.finished_at)),
    pair('Last heartbeat at', formatTime(te.last_heartbeat_at)),
    pair('Heartbeat interval', formatDuration(te.heartbeat_interval_seconds)),
    pair('Commit', makeLink(te.task_version_signature, te.commit_url)),
    pair('Version number', te.task_version_number),
    pair('Version text', te.task_version_text),
    pair('Deployment', te.deployment),
    pair('Command', te.process_command),
    pair('Other instance metadata', te.other_instance_metadata ?
      JSON.stringify(te.other_instance_metadata) : 'None'),
    pair('Exit code', te.exit_code),
    pair('Stop reason', te.stop_reason),
    pair('Stopped by', te.killed_by),
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
    pair('Run as service', formatBoolean(te.is_service)),
    pair('Max concurrency', formatNumber(te.task_max_concurrency)),
    pair('Max conflicting age', formatDuration(te.max_conflicting_age_seconds)),
    pair('Prevent offline execution', formatBoolean(te.prevent_offline_execution)),
    pair('Max Task retries', formatNumber(te.process_max_retries)),
    pair('Termination grace period', formatDuration(te.process_termination_grace_period_seconds)),
    pair('Schedule', te.schedule),
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
    pair('API base URL', te.api_base_url),
    pair('Execution method', tem.type)
  ];

  switch (tem.type) {
    case EXECUTION_METHOD_TYPE_AWS_ECS:
      rows = rows.concat([
    pair('ECS launch type', tem.launch_type),
    pair('ECS cluster', makeLink(tem.cluster_arn, tem.cluster_infrastructure_website_url)),
    pair('ECS task definition ARN', makeLink(tem.task_definition_arn,
      tem.task_definition_infrastructure_website_url)),
    pair('ECS task ARN', makeLink(tem.task_arn, te.infrastructure_website_url)),
    pair('ECS execution role', makeLink(tem.execution_role,
      tem.execution_role_infrastructure_website_url)),
    pair('ECS task role', makeLink(tem.task_role,
      tem.task_role_infrastructure_website_url)),
    pair('ECS platform version', tem.platform_version),
    pair('Subnet(s) ', makeLinks(tem.subnets, tem.subnet_infrastructure_website_urls)),
    pair('Security group(s) ', makeLinks(tem.security_groups, tem.security_group_infrastructure_website_urls)),
    pair('Assign public IP', (tem.assign_public_ip === null) ? 'Unknown' :
      (tem.assign_public_ip ? 'ENABLED' : 'DISABLED')),
    pair('Allocated CPU units', formatNumber(tem.allocated_cpu_units)),
    pair('Allocated memory (MB)', formatNumber(tem.allocated_memory_mb))
      ]);
    break;

    default:
    break;
  };

  rows = rows.concat([
     pair('Workflow Execution',
      te.workflow_task_instance_execution?.workflow_execution ?
      makeLink(te.workflow_task_instance_execution.workflow_execution.uuid,
        '/workflow_executions/' +
        te.workflow_task_instance_execution.workflow_execution.uuid) :
      'N/A'),
  ]);

  /*,
  pair('PagerDuty notified at ', pe.pagerduty_event_sent_at, true),
  pair('PagerDuty event severity ', pe.pagerduty_event_severity), */

	return (
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
	);
}

export default TaskExecutionDetails;