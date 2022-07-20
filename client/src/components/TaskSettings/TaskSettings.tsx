import React from 'react';

import {
  formatNumber, formatDuration, timeFormat,
  makeLink, makeLinks
} from "../../utils";

import {
  RunEnvironment, Task,
  LegacyTaskAwsEcsExecutionMethodCapability,
  AwsLambdaExecutionMethodCapability
} from '../../types/domain_types';

import { Table } from 'react-bootstrap';

import BooleanIcon from '../common/BooleanIcon';
import { EXECUTION_METHOD_TYPE_AWS_ECS, EXECUTION_METHOD_TYPE_AWS_LAMBDA } from '../../utils/constants';

function pair(name: string, value: any) {
  return { name, value: value ?? 'N/A' };
}

interface Props {
  task: Task;
  runEnvironment?: RunEnvironment
}

const TaskSettings = ({ task, runEnvironment }: Props) => {
  const execMethod = task.execution_method_capability;
  const execMethodType = task.execution_method_type;
  const execMethodDetails = task.execution_method_capability_details;
  const runEnvExecMethod = (runEnvironment?.execution_method_capabilities ?? [])[0] as any;

  let rows = [
    pair('Created by', task.created_by_user ?? 'N/A'),
    pair('Created at', timeFormat(task.created_at, true)),
    pair('Updated at', timeFormat(task.updated_at, true)),
    pair('Desired service concurrency', ((task.service_instance_count === null) ? 'N/A' :
      formatNumber(task.service_instance_count))),
    pair('Min service concurrency', ((task.min_service_instance_count === null) ? 'N/A' :
      formatNumber(task.min_service_instance_count))),
    pair('Max concurrency', ((task.max_concurrency === null) ? 'Unlimited' :
      formatNumber(task.max_concurrency))),
    pair('Max age', formatDuration(task.max_age_seconds)),
    pair('Heartbeat interval', formatDuration(task.heartbeat_interval_seconds)),
    pair('Max heartbeat delay before alert',
      formatDuration(task.max_heartbeat_lateness_before_alert_seconds)),
    pair('Max heartbeat delay before abandonment',
      formatDuration(task.max_heartbeat_lateness_before_abandonment_seconds)),
    pair('Max manual start delay before alert',
      formatDuration(task.max_manual_start_delay_before_alert_seconds)),
    pair('Max manual start delay before abandonment',
      formatDuration(task.max_manual_start_delay_before_abandonment_seconds)),
    pair('Max retries', formatNumber(task.default_max_retries)),
    pair('Passive', <BooleanIcon checked={task.passive} />),
    pair('Auto-created', <BooleanIcon checked={task.was_auto_created} />),
    pair('Execution method', execMethodType)
  ];

  if (execMethodType === EXECUTION_METHOD_TYPE_AWS_ECS) {
    const awsEcsEmc = execMethod as LegacyTaskAwsEcsExecutionMethodCapability;
    let execMethodRows = [
      pair('ECS task definition ARN', makeLink(awsEcsEmc.task_definition_arn,
        awsEcsEmc.task_definition_infrastructure_website_url)),
      pair('Supported launch types',
        awsEcsEmc.supported_launch_types ? awsEcsEmc.supported_launch_types.join(', ') : 'N/A'),
      pair('Default launch type', awsEcsEmc.default_launch_type),
      pair('ECS cluster ARN', awsEcsEmc.default_cluster_arn ?
        makeLink(awsEcsEmc.default_cluster_arn, awsEcsEmc.default_cluster_infrastructure_website_url) :
        <span>Default ({
          makeLink(runEnvExecMethod?.default_cluster_arn ?? 'N/A',
            runEnvExecMethod?.default_cluster_infrastructure_website_url)
        })
        </span>),
      pair('ECS execution role ARN', awsEcsEmc.default_execution_role ?
        makeLink(awsEcsEmc.default_execution_role, awsEcsEmc.default_execution_role_infrastructure_website_url) :
        <span>Default ({
          makeLink(runEnvExecMethod.default_execution_role, runEnvExecMethod.default_execution_role_infrastructure_website_url)
        })
        </span>),
      pair('ECS task role ARN', awsEcsEmc.default_task_role ?
        makeLink(awsEcsEmc.default_task_role, awsEcsEmc.default_task_role_infrastructure_website_url) :
        <span>Default ({
          makeLink(runEnvExecMethod.default_task_role || '[None]',
            runEnvExecMethod.default_task_role_infrastructure_website_url)
        })
        </span>),
      pair('ECS platform version',
        awsEcsEmc.default_platform_version ??
        runEnvExecMethod.default_platform_version ?? 'LATEST'),
      pair('Subnets', Array.isArray(awsEcsEmc.default_subnets) ?
        makeLinks(awsEcsEmc.default_subnets,
          awsEcsEmc.default_subnet_infrastructure_website_urls) :
        <span>Default ({
          makeLinks(runEnvExecMethod?.default_subnets ?? 'N/A',
            runEnvExecMethod?.default_subnet_infrastructure_website_urls)
        })
        </span>),
      pair('Security groups', Array.isArray(awsEcsEmc.default_security_groups) ?
        makeLinks(awsEcsEmc.default_security_groups,
          awsEcsEmc.default_security_group_infrastructure_website_urls) :
        <span>Default ({
          makeLinks(runEnvExecMethod?.default_security_groups ?? 'N/A',
            runEnvExecMethod?.default_security_group_infrastructure_website_urls)
        })
        </span>),
      pair('Assign public IP?', <BooleanIcon checked={awsEcsEmc.default_assign_public_ip} />),
      pair('Allocated CPU units', awsEcsEmc.allocated_cpu_units ?? 'N/A'),
      pair('Allocated memory', awsEcsEmc.allocated_memory_mb ?
        (awsEcsEmc.allocated_memory_mb + ' MB') : 'N/A'),
    ];

    const serviceInfo = task.current_service_info;

    if (serviceInfo) {
      execMethodRows.push(pair('Current service info', <span/>))
      execMethodRows.push(pair('  ECS service ARN',
        makeLink(serviceInfo.service_arn, serviceInfo.service_infrastructure_website_url)));
    }

    const serviceOptions = awsEcsEmc.service_options;

    if (serviceOptions) {
      execMethodRows.push(pair('Service options', <span/>));

      execMethodRows.push(pair('Propagate tags',
         serviceOptions.propagate_tags || 'Default'));

      execMethodRows.push(pair('Deployment options', <span/>));
      execMethodRows.push(pair('Force new deployment?',
         <BooleanIcon checked={serviceOptions.force_new_deployment} />));
      execMethodRows.push(pair('Enable circuit breaker?',
         <BooleanIcon checked={serviceOptions.deploy_enable_circuit_breaker} />));
      execMethodRows.push(pair('Rollback on failure?',
         <BooleanIcon checked={serviceOptions.deploy_rollback_on_failure} />));

      if (serviceOptions.load_balancers.length > 0) {
        execMethodRows.push(pair('Load balancer health check grace period',
          formatDuration(serviceOptions.load_balancer_health_check_grace_period_seconds)));

        serviceOptions.load_balancers.forEach((loadBalancer, index) => {
          execMethodRows.push(pair('Load balancer ' + (index + 1), <span />))
          execMethodRows.push(pair('  Target group ARN', loadBalancer.target_group_arn));
          execMethodRows.push(pair('  Container name', loadBalancer.container_name || '(Default)'));
          execMethodRows.push(pair('  Container port', loadBalancer.container_port));
        })
      }
    }

    rows = rows.concat(execMethodRows);
  } else if (execMethodType === EXECUTION_METHOD_TYPE_AWS_LAMBDA) {
    const awsLambdaEmc = execMethodDetails as AwsLambdaExecutionMethodCapability;
    let execMethodRows = [
      pair('Function ARN', makeLink(awsLambdaEmc.function_arn,
        awsLambdaEmc.infrastructure_website_url)),
      pair('Function version', awsLambdaEmc.function_version),
      pair('Allocated memory', awsLambdaEmc.function_memory_mb ?
        (awsLambdaEmc.function_memory_mb + ' MB') : 'N/A'),
      pair('Init type', awsLambdaEmc.init_type),
      pair('Runtime ID', awsLambdaEmc.runtime_id),
      pair('.NET PreJIT', awsLambdaEmc.dotnet_prejit),
    ]

    rows = rows.concat(execMethodRows);
  }

	return (
    <section>
      <Table size="sm">
        <tbody>
          {
            rows.map(row => (
              <tr key={row.name}>
                <td style={{fontWeight: 'bold'}}>
                  {row.name}
                </td>
                <td align="left">
                  {row.value}
                </td>
              </tr>
            ))
          }
        </tbody>
      </Table>
    </section>
	);
}

export default TaskSettings;