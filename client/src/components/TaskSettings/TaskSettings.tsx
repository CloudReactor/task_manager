import * as React from 'react';
import { useState } from 'react';
import Checkbox from '@mui/material/Checkbox';
import Radio from '@mui/material/Radio';
import FormControlLabel from '@mui/material/FormControlLabel';
import IconButton from '@mui/material/IconButton';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';

import {
  formatNumber, formatDuration, timeFormat,
  makeLink, makeLinks
} from "../../utils";
import { INHERIT_SENTINEL } from "../../utils/api";

import {
  DEFAULT_NAME,
  INFRASTRUCTURE_TYPE_AWS,
  EXECUTION_METHOD_TYPE_AWS_ECS,
  SERVICE_PROVIDER_AWS_ECS,
  EXECUTION_METHOD_TYPE_AWS_LAMBDA,
  EXECUTION_METHOD_TYPE_AWS_CODEBUILD,
  AWS_ECS_ALL_SUPPORTED_LAUNCH_TYPES
} from '../../utils/constants';

import {
  RunEnvironment, Task,
  AwsEcsExecutionMethodSettings,
  AwsLambdaExecutionMethodCapability,
  AwsCodeBuildExecutionMethodCapability,
  AwsInfrastructureSettings,
  AwsEcsServiceSettings,
  CapacityProviderStrategyItem
} from '../../types/domain_types';

import { Col, Row, Table, Button } from 'react-bootstrap';

import BooleanIcon from '../common/BooleanIcon';
import BadgeListEditor from '../BadgeListEditor';

interface NameValuePair {
  name: string;
  value: any;
  fieldName?: string;
  fieldType?: 'text' | 'number' | 'checkbox' | 'tristate' | 'select' | 'badgelist' | 'tags' | 'capacityProviderStrategy' | 'checkboxlist';
  fieldOptions?: string[];
  placeholder?: string;
  width?: number;
  allowInherit?: boolean;
}

function pair(name: string, value: any, fieldName?: string, 
  fieldType?: 'text' | 'number' | 'checkbox' | 'tristate' | 'select' | 'badgelist' | 'tags' | 'capacityProviderStrategy' | 'checkboxlist', fieldOptions?: string[],
  placeholder?: string, width?: number, allowInherit?: boolean
): NameValuePair {
  return { name, value: value ?? 'N/A', fieldName, fieldType, fieldOptions, placeholder, width, allowInherit };
}

interface Props {
  task: Task;
  runEnvironment?: RunEnvironment;
  onSave?: (data: any) => Promise<void>;
  isMutationAllowed?: boolean;
}

const TaskSettings = ({ task, runEnvironment, onSave, isMutationAllowed }: Props) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [localData, setLocalData] = useState<any>({});
  const [saveError, setSaveError] = useState<string | null>(null);
  const [newTagKey, setNewTagKey] = useState('');
  const [newTagValue, setNewTagValue] = useState('');
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

    pair('Allocated CPU units', task.allocated_cpu_units, 'allocated_cpu_units', 'number'),
    pair('Allocated memory',
      task.allocated_memory_mb ? `${task.allocated_memory_mb} MB` : null, 'allocated_memory_mb', 'number'),

    pair('Desired service concurrency', ((task.service_instance_count === null) ? 'N/A' :
      formatNumber(task.service_instance_count)), 'service_instance_count', 'number'),
    pair('Min service concurrency', ((task.min_service_instance_count === null) ? 'N/A' :
      formatNumber(task.min_service_instance_count)), 'min_service_instance_count', 'number'),
    pair('Max concurrency', ((task.max_concurrency === null) ? 'Unlimited' :
      formatNumber(task.max_concurrency)), 'max_concurrency', 'number'),
    pair('Max age', formatDuration(task.max_age_seconds), 'max_age_seconds', 'number'),
    pair('Heartbeat interval', formatDuration(task.heartbeat_interval_seconds), 'heartbeat_interval_seconds', 'number'),
    pair('Max heartbeat delay before alert',
      formatDuration(task.max_heartbeat_lateness_before_alert_seconds), 'max_heartbeat_lateness_before_alert_seconds', 'number'),
    pair('Max heartbeat delay before abandonment',
      formatDuration(task.max_heartbeat_lateness_before_abandonment_seconds), 'max_heartbeat_lateness_before_abandonment_seconds', 'number'),
    pair('Max manual start delay before alert',
      formatDuration(task.max_manual_start_delay_before_alert_seconds), 'max_manual_start_delay_before_alert_seconds', 'number'),
    pair('Max manual start delay before abandonment',
      formatDuration(task.max_manual_start_delay_before_abandonment_seconds), 'max_manual_start_delay_before_abandonment_seconds', 'number'),
    pair('Max retries', formatNumber(task.default_max_retries), 'default_max_retries', 'number'),
    pair('Passive', <BooleanIcon checked={task.passive} />, 'passive', 'checkbox'),
    pair('Auto-created', <BooleanIcon checked={task.was_auto_created} />),
    pair('Execution method', execMethodType)
  ];

  if (execMethodType === EXECUTION_METHOD_TYPE_AWS_ECS) {
    const awsEcsEmc = execMethodDetails as AwsEcsExecutionMethodSettings;
    const runEnvAwsEcsSettings = runEnvExecMethodSettings?.[EXECUTION_METHOD_TYPE_AWS_ECS]?.[DEFAULT_NAME]?.settings;

    const execMethodRows = [
      pair('ECS task definition ARN', makeLink(awsEcsEmc.task_definition_arn,
        awsEcsEmc.task_definition_infrastructure_website_url),
        'execution_method_capability_details.task_definition_arn', 'text', undefined, undefined, 1120),
      pair('Supported launch types',
        Array.isArray(awsEcsEmc.supported_launch_types) ? awsEcsEmc.supported_launch_types.join(', ') : 'N/A',
        'execution_method_capability_details.supported_launch_types', 'checkboxlist', AWS_ECS_ALL_SUPPORTED_LAUNCH_TYPES, undefined, undefined, true),
      pair('Default launch type', awsEcsEmc.launch_type ?? 'Inherit',
        'execution_method_capability_details.launch_type', 'select', AWS_ECS_ALL_SUPPORTED_LAUNCH_TYPES),
      ...(awsEcsEmc.capacity_provider_strategy?.length ? [pair('Capacity provider strategy',
        <div style={{marginTop: '0.4rem', marginBottom: '-0.5rem'}}>
          <Row className="g-0 fw-bold pb-1 mb-1">
            <Col xs={8}>Provider</Col>
            <Col xs={2} className="text-end">Weight</Col>
            <Col xs={2} className="text-end">Base</Col>
          </Row>
          {awsEcsEmc.capacity_provider_strategy.map((item: CapacityProviderStrategyItem, index: number) => (
            <Row key={index} className="g-0 py-1">
              <Col xs={8}>{item.capacity_provider}</Col>
              <Col xs={2} className="text-end">{item.weight ?? 'N/A'}</Col>
              <Col xs={2} className="text-end">{item.base ?? 'N/A'}</Col>
            </Row>
          ))}
        </div>,
        'execution_method_capability_details.capacity_provider_strategy', 'capacityProviderStrategy')
      ] : [pair('Capacity provider strategy', 'N/A',
        'execution_method_capability_details.capacity_provider_strategy', 'capacityProviderStrategy')]),
      pair('ECS cluster ARN', awsEcsEmc.cluster_arn ?
        makeLink(awsEcsEmc.cluster_arn, awsEcsEmc.cluster_infrastructure_website_url) :
        <span>Default ({
          runEnvAwsEcsSettings?.cluster_arn ?
            makeLink(runEnvAwsEcsSettings.cluster_arn, runEnvAwsEcsSettings.cluster_infrastructure_website_url) :
            'Inherit'
        })
        </span>,
        'execution_method_capability_details.cluster_arn', 'text', undefined, undefined, 1120),
      pair('ECS execution role ARN', awsEcsEmc.execution_role_arn ?
        makeLink(awsEcsEmc.execution_role_arn, awsEcsEmc.execution_role_infrastructure_website_url) :
        <span>Default ({
          runEnvAwsEcsSettings?.execution_role_arn ?
            makeLink(runEnvAwsEcsSettings.execution_role_arn, runEnvAwsEcsSettings.execution_role_infrastructure_website_url) :
            'Inherit'
        })
        </span>,
        'execution_method_capability_details.execution_role_arn', 'text', undefined, undefined, 1120),
      pair('ECS task role ARN', awsEcsEmc.task_role_arn ?
        makeLink(awsEcsEmc.task_role_arn, awsEcsEmc.task_role_infrastructure_website_url) :
        <span>Default ({
          runEnvAwsEcsSettings?.task_role_arn ?
            makeLink(runEnvAwsEcsSettings.task_role_arn, runEnvAwsEcsSettings.task_role_infrastructure_website_url) :
            'Inherit'
        })
        </span>,
        'execution_method_capability_details.task_role_arn', 'text', undefined, undefined, 1120),
      pair('ECS platform version',
        awsEcsEmc.platform_version ??
        runEnvAwsEcsSettings?.platform_version ?? 'Inherit',
        'execution_method_capability_details.platform_version', 'select', ['1.4.0', 'LATEST']),
      pair('Enable ECS managed tags?',
        awsEcsEmc.enable_ecs_managed_tags == null ? 'Inherit' : <BooleanIcon checked={awsEcsEmc.enable_ecs_managed_tags} />,
        'execution_method_capability_details.enable_ecs_managed_tags', 'tristate', undefined, undefined, undefined, true),
      pair('Enable execute command?',
        awsEcsEmc.enable_execute_command == null ? 'Inherit' : <BooleanIcon checked={awsEcsEmc.enable_execute_command} />,
        'execution_method_capability_details.enable_execute_command', 'tristate', undefined, undefined, undefined, true),
    ];

    if (serviceProviderType === SERVICE_PROVIDER_AWS_ECS) {
      const awsEcsServiceSettings = serviceSettings as AwsEcsServiceSettings;
      const deployConfig = awsEcsServiceSettings?.deployment_configuration;

      const serviceArn = awsEcsServiceSettings.service_arn;

      if (serviceArn) {
        execMethodRows.push(pair('Current service info', <span/>))
        execMethodRows.push(pair('  ECS service ARN',
          makeLink(serviceArn, awsEcsServiceSettings.infrastructure_website_url)));
      }

      execMethodRows.push(pair('Service options', <span/>));
      execMethodRows.push(pair('Scheduling strategy', awsEcsServiceSettings.scheduling_strategy || 'Default',
        'service_settings.scheduling_strategy', 'select', ['REPLICA', 'DAEMON']));
      execMethodRows.push(pair('Availability zone rebalancing', awsEcsServiceSettings.availability_zone_rebalancing || 'Default',
        'service_settings.availability_zone_rebalancing', 'select', ['ENABLED', 'DISABLED']));
      execMethodRows.push(pair('Resource management type', awsEcsServiceSettings.resource_management_type || 'Default',
        'service_settings.resource_management_type', 'select', ['ECS', 'CUSTOMER']));
      execMethodRows.push(pair('Propagate tags', awsEcsServiceSettings.propagate_tags || 'Default',
        'service_settings.propagate_tags', 'select', ['TASK_DEFINITION', 'SERVICE', 'NONE'], undefined, 280));

      execMethodRows.push(pair('Deployment options', <span/>));
      execMethodRows.push(pair('Force new deployment?',
        <BooleanIcon checked={awsEcsServiceSettings?.force_new_deployment ?? false} />,
        'service_settings.force_new_deployment', 'checkbox'));
      execMethodRows.push(pair('Deployment strategy', deployConfig?.strategy || 'ROLLING',
        'service_settings.deployment_configuration.strategy', 'select', ['ROLLING', 'LINEAR', 'CANARY']));
      execMethodRows.push(pair('Maximum %', deployConfig?.maximum_percent ?? 'N/A',
        'service_settings.deployment_configuration.maximum_percent', 'number'));
      execMethodRows.push(pair('Minimum healthy %', deployConfig?.minimum_healthy_percent ?? 'N/A',
        'service_settings.deployment_configuration.minimum_healthy_percent', 'number'));
      execMethodRows.push(pair('Bake time', deployConfig?.bake_time_in_minutes != null
        ? `${deployConfig.bake_time_in_minutes} min` : 'N/A',
        'service_settings.deployment_configuration.bake_time_in_minutes', 'number'));
      execMethodRows.push(pair('Enable circuit breaker?',
        <BooleanIcon checked={deployConfig?.deployment_circuit_breaker?.enable ?? false} />,
        'service_settings.deployment_configuration.deployment_circuit_breaker.enable', 'checkbox'));
      execMethodRows.push(pair('Rollback on failure?',
        <BooleanIcon checked={deployConfig?.deployment_circuit_breaker?.rollback_on_failure ?? false} />,
        'service_settings.deployment_configuration.deployment_circuit_breaker.rollback_on_failure', 'checkbox'));

      const alarms = deployConfig?.alarms;
      if (alarms) {
        execMethodRows.push(pair('Deployment alarms', <span />));
        execMethodRows.push(pair('  Enable alarms?', <BooleanIcon checked={alarms.enable ?? false} />,
          'service_settings.deployment_configuration.alarms.enable', 'checkbox'));
        execMethodRows.push(pair('  Rollback on alarm?', <BooleanIcon checked={alarms.rollback ?? false} />,
          'service_settings.deployment_configuration.alarms.rollback', 'checkbox'));
        execMethodRows.push(pair('  Alarm names', alarms.alarm_names?.join(', ') || 'N/A',
          'service_settings.deployment_configuration.alarms.alarm_names', 'badgelist', [], 'alarm-name', 140));
      }

      if (deployConfig?.strategy === 'LINEAR' && deployConfig.linear_configuration) {
        const lc = deployConfig.linear_configuration;
        execMethodRows.push(pair('Linear step %', lc.step_percent ?? 'N/A',
          'service_settings.deployment_configuration.linear_configuration.step_percent', 'number'));
        execMethodRows.push(pair('Linear step bake time', lc.step_bake_time_in_minutes != null
          ? `${lc.step_bake_time_in_minutes} min` : 'N/A',
          'service_settings.deployment_configuration.linear_configuration.step_bake_time_in_minutes', 'number'));
      }

      if (deployConfig?.strategy === 'CANARY' && deployConfig.canary_configuration) {
        const cc = deployConfig.canary_configuration;
        execMethodRows.push(pair('Canary %', cc.canary_percent ?? 'N/A',
          'service_settings.deployment_configuration.canary_configuration.canary_percent', 'number'));
        execMethodRows.push(pair('Canary bake time', cc.canary_bake_time_in_minutes != null
          ? `${cc.canary_bake_time_in_minutes} min` : 'N/A',
          'service_settings.deployment_configuration.canary_configuration.canary_bake_time_in_minutes', 'number'));
      }

      const lifecycleHooks = deployConfig?.lifecycle_hooks;
      if (lifecycleHooks?.length) {
        execMethodRows.push(pair('Lifecycle hooks',
          <div style={{marginTop: '0.4rem', marginBottom: '-0.5rem'}}>
            <Row className="g-0 fw-bold pb-1 mb-1">
              <Col xs={6}>Hook target ARN</Col>
              <Col xs={6}>Lifecycle stages</Col>
            </Row>
            {lifecycleHooks.map((hook, i) => (
              <Row key={i} className="g-0 py-1">
                <Col xs={6}>{hook.hook_target_arn || 'N/A'}</Col>
                <Col xs={6}>{hook.lifecycle_stages?.join(', ') || 'N/A'}</Col>
              </Row>
            ))}
          </div>
        ));
      }

      const loadBalancers = awsEcsServiceSettings.load_balancers
      const healthCheckGracePeriod = awsEcsServiceSettings.health_check_grace_period_seconds

      if (loadBalancers?.length) {
        execMethodRows.push(pair('Load balancer health check grace period',
          formatDuration(healthCheckGracePeriod ?? null),
          'service_settings.health_check_grace_period_seconds', 'number'));

        loadBalancers.forEach((loadBalancer, index) => {
          execMethodRows.push(pair('Load balancer ' + (index + 1), <span />));
          execMethodRows.push(pair('  Target group ARN',
            makeLink(loadBalancer.target_group_arn, loadBalancer.target_group_infrastructure_website_url)));
          if (loadBalancer.load_balancer_name) {
            execMethodRows.push(pair('  Load balancer name', loadBalancer.load_balancer_name));
          }
          execMethodRows.push(pair('  Container name', loadBalancer.container_name || '(Default)'));
          execMethodRows.push(pair('  Container port', loadBalancer.container_port));
          const adv = loadBalancer.advanced_configuration;
          if (adv) {
            execMethodRows.push(pair('  Alternate target group ARN',
              makeLink(adv.alternate_target_group_arn, adv.alternate_target_group_infrastructure_website_url)));
            if (adv.production_listener_rule) {
              execMethodRows.push(pair('  Production listener rule', adv.production_listener_rule));
            }
            if (adv.test_listener_rule) {
              execMethodRows.push(pair('  Test listener rule', adv.test_listener_rule));
            }
          }
        });
      }

      const serviceRegistries = awsEcsServiceSettings.service_registries;
      if (serviceRegistries?.length) {
        execMethodRows.push(pair('Service registries',
          <div style={{marginTop: '0.4rem', marginBottom: '-0.5rem'}}>
            <Row className="g-0 fw-bold pb-1 mb-1">
              <Col xs={6}>Registry ARN</Col>
              <Col xs={6} className="text-end">Port</Col>
            </Row>
            {serviceRegistries.map((reg, i) => (
              <Row key={i} className="g-0 py-1">
                <Col xs={6}>{reg.registry_arn || 'N/A'}</Col>
                <Col xs={6} className="text-end">{reg.port ?? 'N/A'}</Col>
              </Row>
            ))}
            <Row className="g-0 fw-bold pt-1 mt-1">
              <Col xs={6}>Container name</Col>
              <Col xs={6} className="text-end">Container port</Col>
            </Row>
            {serviceRegistries.map((reg, i) => (
              <Row key={i} className="g-0 py-1">
                <Col xs={6}>{reg.container_name || 'N/A'}</Col>
                <Col xs={6} className="text-end">{reg.container_port ?? 'N/A'}</Col>
              </Row>
            ))}
          </div>
        ));
      }

      const scc = awsEcsServiceSettings.service_connect_configuration;
      if (scc) {
        execMethodRows.push(pair('Service Connect', <span />));
        execMethodRows.push(pair('  Enabled?', <BooleanIcon checked={scc.enabled ?? false} />));
        execMethodRows.push(pair('  Namespace', scc.namespace || 'N/A'));
        if (scc.services?.length) {
          execMethodRows.push(pair('  Services',
            <div style={{marginTop: '0.4rem', marginBottom: '-0.5rem'}}>
              <Row className="g-0 fw-bold pb-1 mb-1">
                <Col xs={3}>Port name</Col>
                <Col xs={3}>Discovery name</Col>
                <Col xs={6} className="text-end">Ingress port override</Col>
              </Row>
              {scc.services.map((svc, i) => (
                <Row key={i} className="g-0 py-1">
                  <Col xs={3}>{svc.port_name || 'N/A'}</Col>
                  <Col xs={3}>{svc.discovery_name || 'N/A'}</Col>
                  <Col xs={6} className="text-end">{svc.ingress_port_override ?? 'N/A'}</Col>
                </Row>
              ))}
            </div>
          ));
        }
        if (scc.log_configuration) {
          execMethodRows.push(pair('  Log driver', scc.log_configuration.log_driver || 'N/A'));
        }
      }

      const volumeConfigurations = awsEcsServiceSettings.volume_configurations;
      if (volumeConfigurations?.length) {
        execMethodRows.push(pair('Volume configurations',
          <div style={{marginTop: '0.4rem', marginBottom: '-0.5rem'}}>
            <Row className="g-0 fw-bold pb-1 mb-1">
              <Col xs={3}>Name</Col>
              <Col xs={3}>Filesystem</Col>
              <Col xs={3}>Volume type</Col>
              <Col xs={3} className="text-end">Size (GiB)</Col>
            </Row>
            {volumeConfigurations.map((vol, i) => (
              <Row key={i} className="g-0 py-1">
                <Col xs={3}>{vol.name}</Col>
                <Col xs={3}>{vol.managed_ebs_volume?.filesystem_type || 'N/A'}</Col>
                <Col xs={3}>{vol.managed_ebs_volume?.volume_type || 'N/A'}</Col>
                <Col xs={3} className="text-end">{vol.managed_ebs_volume?.size_in_gib ?? 'N/A'}</Col>
              </Row>
            ))}
          </div>
        ));
      }

      const vpcLatticeConfigurations = awsEcsServiceSettings.vpc_lattice_configurations;
      if (vpcLatticeConfigurations?.length) {
        execMethodRows.push(pair('VPC Lattice configurations',
          <div style={{marginTop: '0.4rem', marginBottom: '-0.5rem'}}>
            <Row className="g-0 fw-bold pb-1 mb-1">
              <Col xs={9}>Target group ARN</Col>
              <Col xs={3} className="text-end">Port name</Col>
            </Row>
            {vpcLatticeConfigurations.map((vlc, i) => (
              <Row key={i} className="g-0 py-1">
                <Col xs={9}>{makeLink(vlc.target_group_arn, vlc.target_group_infrastructure_website_url)}</Col>
                <Col xs={3} className="text-end">{vlc.port_name || 'N/A'}</Col>
              </Row>
            ))}
          </div>
        ));
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
    const runEnvAwsCodeBuildSettings = runEnvExecMethodSettings?.[EXECUTION_METHOD_TYPE_AWS_CODEBUILD]?.[DEFAULT_NAME]?.settings;
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
        <BooleanIcon checked={awsCodeBuildEmc.privileged_mode ?? false} /> : 'N/A'),
      pair('Assumed role ARN', awsCodeBuildEmc.assumed_role_arn ?
        makeLink(awsCodeBuildEmc.assumed_role_arn, awsCodeBuildEmc.assumed_role_infrastructure_website_url) :
        <span>Default ({
          makeLink(runEnvAwsCodeBuildSettings?.assumed_role_arn, runEnvAwsCodeBuildSettings?.assumed_role_infrastructure_website_url)
        })
        </span>),
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
              'N/A'),
              'infrastructure_settings.network.region', 'text', undefined, undefined, 260, true),
            pair('Subnets', Array.isArray(awsNetworkSettings.subnets) ?
              makeLinks(awsNetworkSettings.subnets,
                awsNetworkSettings.subnet_infrastructure_website_urls) :
              <span>Run Environment default ({
                makeLinks(runEnvDefaultAwsNetworkSettings?.subnets ?? [],
                  runEnvDefaultAwsNetworkSettings?.subnet_infrastructure_website_urls)
              })
              </span>,
              'infrastructure_settings.network.subnets', 'badgelist', [], 'subnet-0123456789abcdef', 140, true),
            pair('Security groups', Array.isArray(awsNetworkSettings.security_groups) ?
              makeLinks(awsNetworkSettings.security_groups,
                awsNetworkSettings.security_group_infrastructure_website_urls) :
              <span>Run Environment default ({
                makeLinks(runEnvDefaultAwsNetworkSettings?.security_groups ?? [],
                  runEnvDefaultAwsNetworkSettings?.security_group_infrastructure_website_urls)
              })
              </span>,
              'infrastructure_settings.network.security_groups', 'badgelist', [], 'sg-0123456789abcdef', 140, true),
            pair('Assign public IP?', <BooleanIcon checked={awsNetworkSettings.assign_public_ip ?? false} />,
              'infrastructure_settings.network.assign_public_ip', 'tristate'),
          ]);
        }

        const awsLogging = awsSettings.logging;

        if (awsLogging) {
          infraRows = infraRows.concat([
            pair('Logging', ''),
            pair('Log Driver', awsLogging.driver,
              'infrastructure_settings.logging.driver', 'text')
          ]);

          const loggingOptions = awsLogging.options;

          if (loggingOptions?.group || awsLogging.infrastructure_website_url) {
            infraRows.push(pair('Log Group',
              makeLink(loggingOptions?.group ?? 'View',
                awsLogging.infrastructure_website_url),
              'infrastructure_settings.logging.options.group', 'text', undefined, undefined, 1120));
          }

          if (loggingOptions) {
            infraRows = infraRows.concat([
              pair('Stream Prefix', loggingOptions.stream_prefix,
                'infrastructure_settings.logging.options.stream_prefix', 'text', undefined, undefined, 1120),
            ]);
          }
        }

        const tags = awsSettings?.tags;

        if (tags) {
          infraRows.push(pair('Tags',
            <table className="table table-borderless table-sm mb-0" style={{ marginBottom: 0 }}>
              <tbody>
                {Object.entries(tags).map(([k, v]) => (
                  <tr key={k}>
                    <td style={{ padding: '0.15rem 0.5rem 0.15rem 0', fontWeight: 'bold', width: '35%' }}>{k}</td>
                    <td style={{ padding: '0.15rem 0.5rem 0.15rem 0' }}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>,
            'infrastructure_settings.tags', 'tags'));
        } else {
          infraRows.push(pair('Tags', '(None)', 'infrastructure_settings.tags', 'tags'));
        }
      }
      break;

      default:
      break;
    }

    rows = rows.concat(infraRows);
  }

  const handleEdit = () => {
    setIsEditing(true);
    if (!localData.infrastructure_settings?.tags) {
      const currentTags = (task.infrastructure_settings as AwsInfrastructureSettings)?.tags;
      if (currentTags) {
        setLocalData((prev: any) => ({
          ...prev,
          infrastructure_settings: {
            ...prev.infrastructure_settings,
            tags: { ...currentTags },
          },
        }));
      }
    }
    setSaveError(null);
  };

  const commitPendingTagRow = (data: any) => {
    const key = newTagKey.trim();
    if (!key) return data;

    const next = { ...data };
    next.infrastructure_settings = {
      ...(next.infrastructure_settings ?? {}),
      tags: {
        ...((next.infrastructure_settings?.tags && typeof next.infrastructure_settings.tags === 'object') ? next.infrastructure_settings.tags : {}),
      },
    };
    next.infrastructure_settings.tags[key] = newTagValue;
    return next;
  };

  const handleCancel = () => {
    setIsEditing(false);
    setLocalData({});
    setNewTagKey('');
    setNewTagValue('');
    setSaveError(null);
  };

  const handleSave = async () => {
    if (!onSave) return;

    setIsSaving(true);
    setSaveError(null);

    try {
      const payload = commitPendingTagRow(localData);
      await onSave(payload);
      setIsEditing(false);
      setLocalData({});
      setNewTagKey('');
      setNewTagValue('');
    } catch (err: any) {
      setSaveError(err?.message || 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const getFieldValue = (fieldName: string) => {
    const parts = fieldName.split('.');
    let val: any = localData;
    for (const part of parts) {
      if (val == null || !Object.prototype.hasOwnProperty.call(val, part)) {
        val = undefined;
        break;
      }
      val = val[part];
    }
    if (val !== undefined) return val;
    val = task as any;
    for (const part of parts) {
      val = val?.[part];
    }
    return val;
  };

  const setFieldValue = (fieldName: string, value: any) => {
    const parts = fieldName.split('.');
    if (parts.length === 1) {
      setLocalData((prev: any) => ({ ...prev, [fieldName]: value }));
      return;
    }
    setLocalData((prev: any) => {
      const next = { ...prev };
      let obj = next;
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        obj[part] = obj[part] ? { ...obj[part] } : {};
        obj = obj[part];
      }
      obj[parts[parts.length - 1]] = value;
      return next;
    });
  };

  const renderEditableField = (pair: NameValuePair) => {
    const { name, fieldName, fieldType, fieldOptions, placeholder, width, allowInherit } = pair;
    const finalFieldName = fieldName ?? name;

    const fieldValue = getFieldValue(finalFieldName);
    const isInheritSelected = allowInherit && fieldValue === INHERIT_SENTINEL;
    const controlDisabled = allowInherit && isInheritSelected;
    const effectiveFieldValue = isInheritSelected
      ? (fieldType === 'badgelist' ? null : '')
      : fieldValue;

    const handleSpecify = () => {
      if (!isInheritSelected) return;
      if (fieldType === 'badgelist') {
        setFieldValue(finalFieldName, []);
      } else {
        setFieldValue(finalFieldName, '');
      }
    };

    const renderWithInherit = (control: React.ReactNode) => {
      if (!allowInherit) return control;
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', fontSize: '0.9rem' }}>
            <FormControlLabel
              control={<Radio size="small" checked={!isInheritSelected} onChange={handleSpecify} />}
              label="Override"
            />
            <FormControlLabel
              control={<Radio size="small" checked={isInheritSelected} onChange={() => setFieldValue(finalFieldName, INHERIT_SENTINEL)} />}
              label="Inherit"
            />
          </div>
          {control}
        </div>
      );
    };

    if (fieldType === 'checkbox') {
      return (
        <Checkbox
          checked={!!fieldValue}
          onChange={(e) => setFieldValue(finalFieldName, e.target.checked)}
          size="small"
          sx={{ padding: '0px' }}
        />
      );
    }

    if (fieldType === 'tristate') {
      const isIndeterminate = fieldValue === null || fieldValue === undefined || fieldValue === INHERIT_SENTINEL;
      const nextValue = isIndeterminate ? true : (fieldValue === true ? false : INHERIT_SENTINEL);
      return (
        <Checkbox
          checked={isIndeterminate ? false : !!fieldValue}
          indeterminate={isIndeterminate}
          onChange={() => setFieldValue(finalFieldName, nextValue)}
          size="small"
          sx={{ padding: '0px' }}
        />
      );
    }

    if (fieldType === 'number') {
      return renderWithInherit(
        <input
          type="number"
          value={effectiveFieldValue ?? ''}
          onChange={(e) => setFieldValue(finalFieldName, e.target.value ? parseInt(e.target.value) : null)}
          style={{ width: '140px' }}
          disabled={controlDisabled}
        />
      );
    }

    if (fieldType === 'badgelist') {
      return renderWithInherit(
        <BadgeListEditor
          value={Array.isArray(effectiveFieldValue) ? effectiveFieldValue : null}
          placeholder={placeholder}
          onChange={(newValue) => setFieldValue(finalFieldName, newValue)}
          disabled={controlDisabled}
        />
      );
    }

    if (fieldType === 'checkboxlist') {
      const activeValues = Array.isArray(effectiveFieldValue) ? effectiveFieldValue : [];
      const toggleValue = (option: string) => {
        const next = activeValues.includes(option)
          ? activeValues.filter((value) => value !== option)
          : [...activeValues, option];
        setFieldValue(finalFieldName, next);
      };
      return renderWithInherit(
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
          {fieldOptions?.map((option) => (
            <FormControlLabel
              key={option}
              control={
                <Checkbox
                  size="small"
                  checked={activeValues.includes(option)}
                  onChange={() => toggleValue(option)}
                  disabled={controlDisabled}
                  sx={{ padding: '0px' }}
                />
              }
              label={option}
              style={{ margin: 0 }}
              sx={{ margin: 0, '& .MuiFormControlLabel-label': { marginLeft: '0.2rem' } }}
            />
          ))}
        </div>
      );
    }

    if (fieldType === 'tags') {
      const baseTags = fieldValue ?? ((pair.value && typeof pair.value === 'object') ? pair.value : {});
      const tagsObj = baseTags && typeof baseTags === 'object' ? { ...baseTags } as Record<string, string> : {} as Record<string, string>;
      const tagEntries = Object.entries(tagsObj);
      const saveTags = (nextTags: Record<string, string> | null) => {
        setFieldValue(finalFieldName, nextTags && Object.keys(nextTags).length ? nextTags : null);
      };
      const handleTagKeyChange = (oldKey: string, nextKey: string) => {
        const trimmedKey = nextKey.trim();
        if (!trimmedKey || trimmedKey === oldKey) return;
        const nextTags = { ...tagsObj };
        const value = nextTags[oldKey];
        delete nextTags[oldKey];
        nextTags[trimmedKey] = value;
        saveTags(nextTags);
      };
      const handleTagValueChange = (key: string, nextValue: string) => {
        saveTags({ ...tagsObj, [key]: nextValue });
      };
      const handleRemoveTag = (key: string) => {
        const nextTags = { ...tagsObj };
        delete nextTags[key];
        saveTags(nextTags);
      };
      const handleAddTag = () => {
        const key = newTagKey.trim();
        if (!key) return;
        saveTags({ ...tagsObj, [key]: newTagValue });
        setNewTagKey('');
        setNewTagValue('');
      };

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: '420px' }}>
          {tagEntries.length ? tagEntries.map(([key, value]) => (
            <div key={key} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                value={key}
                onChange={(e) => handleTagKeyChange(key, e.target.value)}
                placeholder="Name"
                style={{ flex: 1 }}
              />
              <input
                value={value}
                onChange={(e) => handleTagValueChange(key, e.target.value)}
                placeholder="Value"
                style={{ flex: 1 }}
              />
              <IconButton
                size="small"
                onClick={() => handleRemoveTag(key)}
                style={{
                  padding: '4px',
                  minWidth: 'auto',
                  alignSelf: 'center',
                  display: 'inline-flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  minHeight: 'auto'
                }}
              >
                <DeleteIcon fontSize="small" style={{ display: 'inline-block', lineHeight: 1, verticalAlign: 'middle', transform: 'translateY(-5px)' }} />
              </IconButton>
            </div>
          )) : (
            <div style={{ color: '#6c757d' }}>No tags defined</div>
          )}
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="text"
              value={newTagKey}
              onChange={(e) => setNewTagKey(e.target.value)}
              placeholder="Name"
              style={{ flex: 1 }}
            />
            <input
              type="text"
              value={newTagValue}
              onChange={(e) => setNewTagValue(e.target.value)}
              placeholder="Value"
              style={{ flex: 1 }}
            />
            <IconButton size="small" onClick={handleAddTag} disabled={!newTagKey.trim()}>
              <AddIcon fontSize="small" style={{ transform: 'translateY(-5px)' }} />
            </IconButton>
          </div>
        </div>
      );
    }

    if (fieldType === 'capacityProviderStrategy') {
      const strategyItems = Array.isArray(fieldValue) ? fieldValue as CapacityProviderStrategyItem[] : [];
      const saveStrategyItems = (nextItems: CapacityProviderStrategyItem[]) => {
        setFieldValue(finalFieldName, nextItems.length ? nextItems : null);
      };
      const handleStrategyChange = (index: number, key: keyof CapacityProviderStrategyItem, value: string | number | null) => {
        const nextItems = strategyItems.map((item, idx) => idx === index ? { ...item, [key]: value } : item);
        saveStrategyItems(nextItems);
      };
      const handleRemoveStrategy = (index: number) => {
        const nextItems = strategyItems.filter((_, idx) => idx !== index);
        saveStrategyItems(nextItems);
      };
      const handleAddStrategy = () => {
        saveStrategyItems([...strategyItems, { capacity_provider: '', weight: null, base: null }]);
      };

      return (
        <div style={{ minWidth: '360px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1fr 1fr 40px', gap: '0.5rem', marginBottom: '0.35rem', fontWeight: 'bold' }}>
            <div>Provider</div>
            <div style={{ textAlign: 'right' }}>Weight</div>
            <div style={{ textAlign: 'right' }}>Base</div>
            <div />
          </div>
          {strategyItems.map((item, index) => (
            <div key={index} style={{ display: 'grid', gridTemplateColumns: '1.8fr 1fr 1fr 40px', gap: '0.5rem', alignItems: 'center', marginBottom: '0.35rem' }}>
              <input
                type="text"
                value={item.capacity_provider ?? ''}
                onChange={(e) => handleStrategyChange(index, 'capacity_provider', e.target.value)}
                placeholder="FARGATE_SPOT"
                style={{ width: '100%' }}
              />
              <input
                type="number"
                value={item.weight ?? ''}
                onChange={(e) => handleStrategyChange(index, 'weight', e.target.value ? parseInt(e.target.value) : null)}
                placeholder="1"
                style={{ width: '100%' }}
              />
              <input
                type="number"
                value={item.base ?? ''}
                onChange={(e) => handleStrategyChange(index, 'base', e.target.value ? parseInt(e.target.value) : null)}
                placeholder="0"
                style={{ width: '100%' }}
              />
              <IconButton
                size="small"
                onClick={() => handleRemoveStrategy(index)}
                style={{
                  padding: '4px',
                  minWidth: 'auto',
                  alignSelf: 'center',
                  display: 'inline-flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  minHeight: 'auto'
                }}
              >
                <DeleteIcon fontSize="small" style={{ display: 'inline-block', lineHeight: 1, verticalAlign: 'middle', transform: 'translateY(-2px)' }} />
              </IconButton>
            </div>
          ))}
          <Button variant="outline-secondary" size="sm" onClick={handleAddStrategy} style={{ marginTop: '0.25rem' }}>
            <AddIcon fontSize="small" style={{ transform: 'translateY(-5px)' }} /> Add row
          </Button>
        </div>
      );
    }

    if (fieldType === 'select') {
      const selectValue = fieldValue === null || fieldValue === undefined
        ? (allowInherit ? INHERIT_SENTINEL : '')
        : fieldValue;
      return renderWithInherit(
        <select
          className="form-select editable-task-settings"
          value={selectValue}
          onChange={(e) => setFieldValue(finalFieldName, e.target.value)}
          style={{
            width: width ? `${width}px` : '140px',
            backgroundColor: '#f8f9fa',
            color: '#212529'
          }}
          disabled={controlDisabled}
        >
          {allowInherit && <option value={INHERIT_SENTINEL}>Inherit</option>}
          {fieldOptions?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
        </select>
      );
    }

    return renderWithInherit(
      <input
        type={fieldType}
        value={effectiveFieldValue ?? ''}
        onChange={(e) => setFieldValue(finalFieldName, e.target.value)}
        placeholder={placeholder}
        style={width ? { width: `${width}px` } : undefined}
        disabled={controlDisabled}
      />
    );
  };

	return (
    <section style={{ overflow: 'visible' }}>
      <style>{`
        .editable-task-settings input[type=number]::-webkit-inner-spin-button,
        .editable-task-settings input[type=number]::-webkit-outer-spin-button {
          -webkit-appearance: none;
          margin: 0;
        }
        .editable-task-settings input[type=number] {
          -moz-appearance: textfield;
          appearance: textfield;
        }
        select.form-select.editable-task-settings {
          background-color: #f8f9fa !important;
          color: #212529 !important;
          background-image: none !important;
          padding-left: 0.75rem !important;
          padding-right: 1.75rem !important;
        }
      `}</style>
      {saveError && (
        <div className="alert alert-danger" role="alert">
          {saveError}
        </div>
      )}

      <div style={{ overflow: 'visible', position: 'relative' }}>
        <Table size="sm" style={{ tableLayout: 'auto', overflow: 'visible' }} className="editable-task-settings">
          <tbody>
            {
              rows.map(row => (
                <tr key={row.name} style={{ overflow: 'visible' }}>
                  <td style={{fontWeight: 'bold', overflow: 'visible', paddingRight: '30px'}}>
                    {row.name}
                  </td>
                  <td align="left" style={{ overflow: 'visible', paddingRight: '50px', position: 'relative', whiteSpace: 'normal', display: 'table-cell' }}>
                    {row.fieldName && isEditing ? renderEditableField(row): row.value}
                  </td>
                </tr>
              ))
            }
            {onSave && (
              <tr>
                <td />
                <td style={{ paddingTop: '1rem' }}>
                  {!isEditing ? (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleEdit}
                      disabled={!isMutationAllowed}
                    >
                      Edit
                    </Button>
                  ) : (
                    <>
                      <Button
                        variant="success"
                        size="sm"
                        onClick={handleSave}
                        disabled={isSaving}
                        style={{ marginRight: '0.5rem' }}
                      >
                        {isSaving ? 'Saving...' : 'Save'}
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleCancel}
                        disabled={isSaving}
                      >
                        Cancel
                      </Button>
                    </>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </Table>
      </div>
    </section>
	);
}

export default TaskSettings;