import React from 'react';

import {
  formatNumber, formatDuration, timeFormat,
  makeLink, makeLinks
} from "../../utils";

import {
  DEFAULT_NAME,
  INFRASTRUCTURE_TYPE_AWS,
  EXECUTION_METHOD_TYPE_AWS_ECS,
  SERVICE_PROVIDER_AWS_ECS,
  EXECUTION_METHOD_TYPE_AWS_LAMBDA,
  EXECUTION_METHOD_TYPE_AWS_CODEBUILD
} from '../../utils/constants';

import {
  RunEnvironment, Task,
  AwsEcsExecutionMethodSettings,
  AwsLambdaExecutionMethodCapability,
  AwsCodeBuildExecutionMethodCapability,
  AwsInfrastructureSettings,
  AwsEcsServiceSettings
} from '../../types/domain_types';

import { Table } from 'react-bootstrap';

import BooleanIcon from '../common/BooleanIcon';

interface NameValuePair {
  name: string;
  value: any;
}

function pair(name: string, value: any): NameValuePair {
  return { name, value: value ?? 'N/A' };
}

interface Props {
  task: Task;
  runEnvironment?: RunEnvironment
}

const TaskSettings = ({ task, runEnvironment }: Props) => {
  const runEnvInfraSettings = runEnvironment?.infrastructure_settings;
  const runEnvExecMethodSettings = runEnvironment?.execution_method_settings;

  const runEnvAwsSettings = runEnvInfraSettings?.[INFRASTRUCTURE_TYPE_AWS];
  const runEnvDefaultAwsNetworkSettings = runEnvAwsSettings?.[DEFAULT_NAME]?.settings?.network;

  const infraType = task.infrastructure_type;
  const infraSettings = task.infrastructure_settings;

  const execMethodType = task.execution_method_type;
  const execMethodDetails = task.execution_method_capability_details;
  const serviceProviderType = task.service_provider_type;
  const serviceSettings = task.service_settings;

  let rows = [
    pair('Created by', task.created_by_user ?? 'N/A'),
    pair('Created at', timeFormat(task.created_at, true)),
    pair('Updated at', timeFormat(task.updated_at, true)),

    pair('Allocated CPU units', task.allocated_cpu_units),
    pair('Allocated memory',
      task.allocated_memory_mb ? `${task.allocated_memory_mb} MB` : null),

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
    const awsEcsEmc = execMethodDetails as AwsEcsExecutionMethodSettings;
    const runEnvAwsEcsSettings = runEnvExecMethodSettings?.[EXECUTION_METHOD_TYPE_AWS_ECS]?.[DEFAULT_NAME]?.settings;

    const execMethodRows = [
      pair('ECS task definition ARN', makeLink(awsEcsEmc.task_definition_arn,
        awsEcsEmc.task_definition_infrastructure_website_url)),
      pair('Supported launch types',
        awsEcsEmc.supported_launch_types ? awsEcsEmc.supported_launch_types.join(', ') : 'N/A'),
      pair('Default launch type', awsEcsEmc.launch_type),
      pair('ECS cluster ARN', awsEcsEmc.cluster_arn ?
        makeLink(awsEcsEmc.cluster_arn, awsEcsEmc.cluster_infrastructure_website_url) :
        <span>Default ({
          makeLink(runEnvAwsEcsSettings?.cluster_arn ?? 'N/A',
            runEnvAwsEcsSettings?.cluster_infrastructure_website_url)
        })
        </span>),
      pair('ECS execution role ARN', awsEcsEmc.execution_role_arn ?
        makeLink(awsEcsEmc.execution_role_arn, awsEcsEmc.execution_role_infrastructure_website_url) :
        <span>Default ({
          makeLink(runEnvAwsEcsSettings?.execution_role_arn, runEnvAwsEcsSettings?.execution_role_infrastructure_website_url)
        })
        </span>),
      pair('ECS task role ARN', awsEcsEmc.task_role_arn ?
        makeLink(awsEcsEmc.task_role_arn, awsEcsEmc.task_role_infrastructure_website_url) :
        <span>Default ({
          makeLink(runEnvAwsEcsSettings?.task_role_arn || '[None]',
            runEnvAwsEcsSettings?.task_role_infrastructure_website_url)
        })
        </span>),
      pair('ECS platform version',
        awsEcsEmc.platform_version ??
        runEnvAwsEcsSettings?.platform_version ?? 'LATEST'),
    ];

    if (serviceProviderType === SERVICE_PROVIDER_AWS_ECS) {
      const awsEcsServiceSettings = serviceSettings as AwsEcsServiceSettings;

      const serviceArn = awsEcsServiceSettings.service_arn;

      if (serviceArn) {
        execMethodRows.push(pair('Current service info', <span/>))
        execMethodRows.push(pair('  ECS service ARN',
          makeLink(serviceArn, awsEcsServiceSettings.infrastructure_website_url)));
      }

      execMethodRows.push(pair('Service options', <span/>));

      execMethodRows.push(pair('Propagate tags',
        awsEcsServiceSettings.propagate_tags || 'Default'));

      execMethodRows.push(pair('Deployment options', <span/>));
      execMethodRows.push(pair('Force new deployment?',
        <BooleanIcon checked={awsEcsServiceSettings?.force_new_deployment ?? false} />));
      execMethodRows.push(pair('Maximum %',
        awsEcsServiceSettings?.deployment_configuration?.maximum_percent ?? 'N/A'));
      execMethodRows.push(pair('Minimum healthy %',
        awsEcsServiceSettings?.deployment_configuration?.minimum_healthy_percent ?? 'N/A'));
      execMethodRows.push(pair('Enable circuit breaker?',
        <BooleanIcon checked={awsEcsServiceSettings?.deployment_configuration?.deployment_circuit_breaker?.enable ?? false} />));
      execMethodRows.push(pair('Rollback on failure?',
        <BooleanIcon checked={awsEcsServiceSettings?.deployment_configuration?.deployment_circuit_breaker?.rollback_on_failure ?? false} />));

      const loadBalancerSettings = awsEcsServiceSettings?.load_balancer_settings;
      const loadBalancers = loadBalancerSettings?.load_balancers;

      if (loadBalancerSettings && loadBalancers?.length) {
        execMethodRows.push(pair('Load balancer health check grace period',
          formatDuration(loadBalancerSettings.health_check_grace_period_seconds)));

        loadBalancers.forEach((loadBalancer, index) => {
          execMethodRows.push(pair('Load balancer ' + (index + 1), <span />))
          execMethodRows.push(pair('  Target group ARN',
            makeLink(loadBalancer.target_group_arn, loadBalancer.target_group_infrastructure_website_url)));
          execMethodRows.push(pair('  Container name', loadBalancer.container_name || '(Default)'));
          execMethodRows.push(pair('  Container port', loadBalancer.container_port));
        })
      }
    }

    rows = rows.concat(execMethodRows);
  } else if (execMethodType === EXECUTION_METHOD_TYPE_AWS_LAMBDA) {
    const awsLambdaEmc = execMethodDetails as AwsLambdaExecutionMethodCapability;
    rows = rows.concat([
      pair('Function name', makeLink(awsLambdaEmc.function_name,
        awsLambdaEmc.infrastructure_website_url)),
      pair('Function ARN', makeLink(awsLambdaEmc.function_arn,
        awsLambdaEmc.infrastructure_website_url)),
      pair('Init type', awsLambdaEmc.init_type),
      pair('Runtime ID', awsLambdaEmc.runtime_id),
      pair('.NET PreJIT', awsLambdaEmc.dotnet_prejit),
    ]);
  } else if (execMethodType === EXECUTION_METHOD_TYPE_AWS_CODEBUILD) {
    const awsCodeBuildEmc = execMethodDetails as AwsCodeBuildExecutionMethodCapability;
    rows = rows.concat([
      pair('Project name', awsCodeBuildEmc.project_name),
      pair('Build ARN', makeLink(awsCodeBuildEmc.build_arn,
        awsCodeBuildEmc.infrastructure_website_url)),
      pair('Source repository', makeLink(awsCodeBuildEmc.source_repo_url,
        awsCodeBuildEmc.source_repo_url)),
      pair('Source version', makeLink(awsCodeBuildEmc.source_version,
        awsCodeBuildEmc.source_version_infrastructure_website_url)),
      pair('Timeout', awsCodeBuildEmc.timeout_in_minutes ?
        `${awsCodeBuildEmc.timeout_in_minutes} minutes` : 'N/A'),
      pair('Queued timeout', awsCodeBuildEmc.queued_timeout_in_minutes ?
        `${awsCodeBuildEmc.queued_timeout_in_minutes} minutes` : 'N/A'),
      pair('Service role', makeLink(awsCodeBuildEmc.service_role,
        awsCodeBuildEmc.service_role_infrastructure_website_url)),
      pair('KMS key ID', awsCodeBuildEmc.kms_key_id ?
        makeLink(awsCodeBuildEmc.kms_key_id, awsCodeBuildEmc.kms_key_infrastructure_website_url) : 'N/A'),
      pair('Environment type', awsCodeBuildEmc.environment_type),
      pair('Compute type', awsCodeBuildEmc.compute_type),
      pair('Build image', awsCodeBuildEmc.build_image),
      pair('Privileged mode?', (typeof awsCodeBuildEmc.privileged_mode === 'boolean') ?
        <BooleanIcon checked={awsCodeBuildEmc.privileged_mode ?? false} /> : 'N/A')
    ]);
  }

  rows.push(pair('Infrastructure provider', infraType));

  if (infraType && infraSettings) {
    let infraRows: NameValuePair[] = [];

    switch (infraType) {
      case INFRASTRUCTURE_TYPE_AWS: {
        const awsSettings = task.infrastructure_settings as AwsInfrastructureSettings;
        const awsNetworkSettings = awsSettings?.network;

        if (awsNetworkSettings) {
          infraRows = infraRows.concat([
            pair('Networking', ''),
            pair('Region', awsNetworkSettings?.region ??
              (runEnvDefaultAwsNetworkSettings?.region ?
              `Run Environment default (${runEnvDefaultAwsNetworkSettings.region})` :
              'N/A')),
            pair('Subnets', Array.isArray(awsNetworkSettings.subnets) ?
              makeLinks(awsNetworkSettings.subnets,
                awsNetworkSettings.subnet_infrastructure_website_urls) :
              <span>Run Environment default ({
                makeLinks(runEnvDefaultAwsNetworkSettings?.subnets ?? [],
                  runEnvDefaultAwsNetworkSettings?.subnet_infrastructure_website_urls)
              })
              </span>),
            pair('Security groups', Array.isArray(awsNetworkSettings.security_groups) ?
              makeLinks(awsNetworkSettings.security_groups,
                awsNetworkSettings.security_group_infrastructure_website_urls) :
              <span>Run Environment default ({
                makeLinks(runEnvDefaultAwsNetworkSettings?.security_groups ?? [],
                  runEnvDefaultAwsNetworkSettings?.security_group_infrastructure_website_urls)
              })
              </span>),
            pair('Assign public IP?', <BooleanIcon checked={awsNetworkSettings.assign_public_ip ?? false} />),
          ]);
        }

        const awsLogging = awsSettings.logging;

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
      }
      break;

      default:
      break;
    }

    rows = rows.concat(infraRows);
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