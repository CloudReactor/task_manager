import {
  plainToInstance
} from 'class-transformer';

import { makeAuthenticatedClient } from '../axios_config';

import React from 'react'

import {
  Group, User, Invitation
} from '../types/website_types';

import {
  NotificationMethod,
  ApiKey,
  Task,
  TaskImpl,
  TaskExecution,
  RunEnvironment,
  Workflow,
  WorkflowExecution,
  PagerDutyProfile,
  WorkflowExecutionSummary,
  WorkflowSummary,
  EmailNotificationProfile
} from '../types/domain_types';

import * as C from './constants';
import * as UIC from './ui_constants';

export interface ResultsPage<T> {
  count: number;
  results: T[];
};

export class ResultsPageImpl<T> implements ResultsPage<T> {
  count = 0;
  results = [];
}

export function makeEmptyResultsPage<T>(): ResultsPage<T> {
  return new ResultsPageImpl()
}

export interface FetchOptions {
  abortSignal?: AbortSignal;
}

export interface PageFetchOptions extends FetchOptions {
  q?: string;
  sortBy?: string;
  descending?: boolean;
  offset?: number;
  maxResults?: number;
}

export const DEFAULT_PAGE_FETCH_OPTIONS: PageFetchOptions = {
  sortBy: 'name',
  offset: 0,
  maxResults: UIC.DEFAULT_PAGE_SIZE,
  descending: false
}

export interface PageFetchWithGroupIdOptions extends PageFetchOptions {
  groupId?: number | null;
}

export interface PageFetchWithGroupIdAndRunEnvironmentOptions
extends PageFetchWithGroupIdOptions {
  runEnvironmentUuids?: string[];
}

export interface PageFetchWithGroupIdAndScopedRunEnvironmentOptions
extends PageFetchWithGroupIdAndRunEnvironmentOptions {
  optionalRunEnvironmentUuid?: string | null;
}

function makePageFetchParams(pageFetchOptions?: PageFetchOptions,
    defaultOptions?: PageFetchOptions): { [key: string]: any } {
  if (defaultOptions) {
    Object.assign({}, pageFetchOptions ?? {}, defaultOptions)
  }

  const {
    q,
    sortBy,
    descending,
    offset,
    maxResults
  } = pageFetchOptions ?? {};

  const params: { [key: string]: any }  = {
    offset,
    limit: maxResults
  };

  if (q) {
    params.search = q;
  }

  if (sortBy) {
    params.ordering = descending ? `-${sortBy}` : sortBy;
  }

  return params;
}

function makePageFetchWithGroupParams(pageFetchOptions?: PageFetchWithGroupIdOptions,
    defaultOptions?: PageFetchWithGroupIdOptions): { [key: string]: any } {
  const params = makePageFetchParams(pageFetchOptions, defaultOptions);

  const groupId = pageFetchOptions?.groupId ?? defaultOptions?.groupId;

  if (groupId) {
    params['created_by_group__id'] = '' + groupId;
  }

  return params;
}

function makePageFetchWithGroupAndRunEnvironmentParams(pageFetchOptions?: PageFetchWithGroupIdAndRunEnvironmentOptions,
    defaultOptions?: PageFetchWithGroupIdAndRunEnvironmentOptions): { [key: string]: any } {
  const params = makePageFetchWithGroupParams(pageFetchOptions, defaultOptions);

  const runEnvironmentUuids = pageFetchOptions?.runEnvironmentUuids ?? defaultOptions?.runEnvironmentUuids;

  if (runEnvironmentUuids) {
    params['run_environment__uuid__in'] = '' + runEnvironmentUuids.join(',');
  }

  return params;
}

function makePageFetchWithGroupAndScopedRunEnvironmentParams(pageFetchOptions?: PageFetchWithGroupIdAndScopedRunEnvironmentOptions,
    defaultOptions?: PageFetchWithGroupIdAndScopedRunEnvironmentOptions): { [key: string]: any } {
  const params = makePageFetchWithGroupAndRunEnvironmentParams(pageFetchOptions, defaultOptions);

  const optionalRunEnvironmentUuid = pageFetchOptions?.optionalRunEnvironmentUuid ??
    defaultOptions?.optionalRunEnvironmentUuid;

  if (optionalRunEnvironmentUuid) {
    params['optional_run_environment__uuid'] = '' + optionalRunEnvironmentUuid;
  }

  return params;
}



export const itemsPerPageOptions: Array<{ value: number; text: number }> = [
  //For testing
  // { value: 5, text: 5 },
  { value: 25, text: 25 },
  { value: 50, text: 50 },
  { value: 100, text: 100 }
];

export async function fetchCurrentUser(fetchOptions?: FetchOptions): Promise<User> {
  const {
    abortSignal
  } = fetchOptions ?? {};

  const response = await makeAuthenticatedClient().get(
    'auth/users/me/', {
      signal: abortSignal
    });
  return response.data as User;
}

export async function fetchUsers(opts? : PageFetchWithGroupIdOptions):
    Promise<ResultsPage<User>> {
  opts = opts ?? {};

  const {
    abortSignal
  } = opts;

  const params = makePageFetchWithGroupParams(opts);

  params.group__id = params.created_by_group__id;
  delete params.created_by_group__id;

  const response = await makeAuthenticatedClient().get(
    'api/v1/users/', {
      signal: abortSignal,
      params
    });

  return response.data as ResultsPage<User>;
}

export async function fetchGroup(id: number, abortSignal?: AbortSignal): Promise<Group> {
  const response = await makeAuthenticatedClient().get(
    'api/v1/groups/' + id + '/', {
    signal: abortSignal
  });
  return response.data as Group;
}

export async function saveGroup(group: any) : Promise<Group> {
  const client = makeAuthenticatedClient();
  const response = await (group.id ? client.patch(
    'api/v1/groups/' + encodeURIComponent(group.id) + '/', group
  ) : client.post('api/v1/groups/', group));

  return response.data as Group;
}

export async function fetchInvitation(invitationCode: string) : Promise<Invitation | null> {
  const response = await makeAuthenticatedClient().get(
    'api/v1/invitations/?confirmation_code=' + encodeURIComponent(invitationCode));
  const {
    results
  } = (response.data as ResultsPage<Invitation>);

  if (results.length === 1) {
    return results[0];
  } else {
    return null;
  }
}

export async function saveInvitation(invitation: any): Promise<boolean> {
  const client = makeAuthenticatedClient();
  const response = await (invitation.uuid ? client.patch(
    'api/v1/invitations/' + encodeURIComponent(invitation.uuid) + '/', invitation
  ) : client.post('api/v1/invitations/', invitation));

  // response.data.result is either created_invitation_for_new_user or
  // added_access_to_existing_user
  // Will be 200 when user already exists
  return (response.status === 201);
}

export async function removeUserFromGroup(username: string, groupName: string): Promise<void> {
  const client = makeAuthenticatedClient();
  await client.post('api/v1/group_memberships/remove/', {
    group: {
      name: groupName
    },
    user: {
      username
    }
  });
}

export async function updateGroupAccessLevelOfUser(username: string,
  groupName: string, accessLevel: number | undefined | null) {
  if (accessLevel === C.ACCESS_LEVEL_OBSERVER) {
    accessLevel = null;
  }

  const client = makeAuthenticatedClient();
  await client.post('api/v1/group_memberships/update_access_level/', {
    group: {
      name: groupName
    },
    user: {
      username
    },
    access_level: accessLevel
  });
}

export async function fetchApiKey(uuid: string, abortSignal?: AbortSignal) {
  const response = await makeAuthenticatedClient().get(
    `api/v1/api_keys/${uuid}/`, {
    signal: abortSignal
  });
  return response.data as ApiKey;
}

export async function saveApiKey(apiKey: any, abortSignal?: AbortSignal) : Promise<ApiKey> {
  const client = makeAuthenticatedClient();
  const response = await (apiKey.uuid ? client.patch(
    'api/v1/api_keys/' + encodeURIComponent(apiKey.uuid) + '/',
    apiKey, { signal: abortSignal }
  ) : client.post('api/v1/api_keys/', apiKey, { signal: abortSignal }));

  return response.data as ApiKey;
}

export async function fetchApiKeys(opts? : PageFetchWithGroupIdOptions):
   Promise<ResultsPage<ApiKey>> {
  opts = opts ?? {};

  const {
    abortSignal
  } = opts;

  const params = makePageFetchWithGroupParams(opts);

  params.group__id = params.created_by_group__id;
  delete params.created_by_group__id;

  const response = await makeAuthenticatedClient().get(
    'api/v1/api_keys/', {
      signal: abortSignal,
      params
    });

  return response.data as ResultsPage<ApiKey>;
}

export async function deleteApiKey(uuid: string, abortSignal?: AbortSignal): Promise<void> {
  const client = makeAuthenticatedClient();
  await client.delete(
    'api/v1/api_keys/' + encodeURIComponent(uuid) + '/', {
      signal: abortSignal
    });
}

export interface WorkflowPageFetchOptions extends PageFetchWithGroupIdAndRunEnvironmentOptions {
  statuses?: string[];
}

export async function fetchWorkflowSummaries(opts?: WorkflowPageFetchOptions)
  : Promise<ResultsPage<WorkflowSummary>> {
  opts = opts ?? {};

  const {
    abortSignal
  } = opts;

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);

  if (opts.statuses) {
    params['latest_workflow_execution__status'] = opts.statuses.join(',');
  }

  const response = await makeAuthenticatedClient().get(
    'api/v1/workflows/', {
      signal: abortSignal,
      params
    });

  return response.data as ResultsPage<WorkflowSummary>;
}

export async function fetchWorkflow(uuid: string, abortSignal?: AbortSignal): Promise<Workflow> {
  const response = await makeAuthenticatedClient().get(
      'api/v1/workflows/' + encodeURIComponent(uuid) + '/', {
        signal: abortSignal
      });
  return response.data as Workflow;
}

export async function saveWorkflow(workflow: any) : Promise<Workflow> {
  const client = makeAuthenticatedClient();
  const response = await (workflow.uuid ? client.patch(
    'api/v1/workflows/' + encodeURIComponent(workflow.uuid) + '/',
    workflow
  ) : client.post('api/v1/workflows/', workflow));

  return response.data as Workflow;
}

export async function deleteWorkflow(uuid: string): Promise<void> {
  const client = makeAuthenticatedClient();
  const response = await client.delete(
    'api/v1/workflows/' + encodeURIComponent(uuid) + '/');

  return response.data;
}

export async function cloneWorkflow(uuid: string, attributes: any,
    abortSignal?: AbortSignal): Promise<Workflow> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/workflows/' + uuid + '/clone/', attributes, {
      signal: abortSignal
    });
  return response.data as Workflow;
}

export interface WorkflowExecutionPageFetchOptions
extends PageFetchWithGroupIdAndRunEnvironmentOptions {
  workflowUuid?: string;
  statuses?: string[];
}



export async function fetchWorkflowExecutionSummaries(
  opts?: WorkflowExecutionPageFetchOptions
) : Promise<ResultsPage<WorkflowExecutionSummary>> {
  opts = opts ?? {};

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);

  const {
    workflowUuid,
    statuses,
    abortSignal
  } = opts;

  if (workflowUuid) {
    params.workflow__uuid = workflowUuid;
  }

  if (statuses) {
    params['status__in'] = statuses.join(',');
  }

  const response = await makeAuthenticatedClient().get('api/v1/workflow_executions/', {
    signal: abortSignal,
    params
  });

  return response.data as ResultsPage<WorkflowExecutionSummary>;
}

export async function fetchWorkflowExecution(uuid: string,
    abortSignal?: AbortSignal): Promise<WorkflowExecution> {
  const response = await makeAuthenticatedClient().get(
      'api/v1/workflow_executions/' + encodeURIComponent(uuid) + '/', {
    signal: abortSignal
  });
  return response.data as WorkflowExecution;
}

export async function startWorkflowExecution(workflowUuid: string,
    abortSignal?: AbortSignal): Promise<WorkflowExecution> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/workflow_executions/',
    {
       workflow: {
         uuid: workflowUuid
       },
       status: C.WORKFLOW_EXECUTION_STATUS_MANUALLY_STARTED
    }, {
      signal: abortSignal
    }
  );
  return response.data as WorkflowExecution;
}

export async function stopWorkflowExecution(uuid: string): Promise<WorkflowExecution> {
  const response = await makeAuthenticatedClient().patch(
    'api/v1/workflow_executions/' + encodeURIComponent(uuid) + '/',
    {
       status: C.WORKFLOW_EXECUTION_STATUS_STOPPING
    }
  );
  return response.data as WorkflowExecution;
}

export async function startWorkflowTaskInstances(
    workflowExecutionUuid: string,
    workflowTaskInstanceUuids: string[]): Promise<WorkflowExecution> {

  const response = await makeAuthenticatedClient().post(
    'api/v1/workflow_executions/' + workflowExecutionUuid + '/workflow_task_instance_executions/',
    {
       workflow_task_instances: workflowTaskInstanceUuids.map(uuid => {
          return { 'uuid': uuid };
       })
    }
  );
  return response.data as WorkflowExecution;
}

export async function retryWorkflowExecution(
    workflowExecutionUuid: string, abortSignal?: AbortSignal): Promise<WorkflowExecution> {

  const response = await makeAuthenticatedClient().post(
    'api/v1/workflow_executions/' + workflowExecutionUuid + '/retry/', null, {
      signal: abortSignal
    });
  return response.data as WorkflowExecution;
}

export async function saveRunEnvironment(uuid: string,
    values: any) : Promise<RunEnvironment> {
  const client = makeAuthenticatedClient();

  const response = await ((!uuid || (uuid === 'new')) ? client.post(
    'api/v1/run_environments/',
    values
  ) : client.patch(`api/v1/run_environments/${uuid}/`, values));

  return response.data as RunEnvironment;
}

export async function fetchNotificationMethods(
  opts? :  PageFetchWithGroupIdAndScopedRunEnvironmentOptions): Promise<ResultsPage<NotificationMethod>> {
  opts = opts ?? {};

  const {
    abortSignal
  } = opts;

  const params = makePageFetchWithGroupAndScopedRunEnvironmentParams(opts);
  const response = await makeAuthenticatedClient().get(
    'api/v1/alert_methods/', {
      signal: abortSignal,
      params
    });

  return response.data as ResultsPage<NotificationMethod>;
}

export async function fetchNotificationMethod(uuid: string, abortSignal?: AbortSignal) {
  const response = await makeAuthenticatedClient().get(
    `api/v1/alert_methods/${uuid}/`, {
      signal: abortSignal
    });
  return response.data as NotificationMethod;
}

export async function saveNotificationMethod(uuid: string, values: any,
    abortSignal?: AbortSignal) : Promise<NotificationMethod> {
  // remove name & url -- only use UUID to associate selected PD profile with this NotificationMethod
  delete values.method_details.profile.name;
  delete values.method_details.profile.url;

  const client = makeAuthenticatedClient();

  const response = await ((!uuid || (uuid === 'new')) ? client.post(
    'api/v1/alert_methods/', values, {
      signal: abortSignal
    }
  ) : client.patch(`api/v1/alert_methods/${uuid}/`, values, {
      signal: abortSignal
    })
  );

  return response.data;
}

export async function cloneNotificationMethod(uuid: string, attributes?: any,
    abortSignal?: AbortSignal): Promise<NotificationMethod> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/alert_methods/' + uuid + '/clone/', attributes || {}, {
        signal: abortSignal
    });
  return response.data as NotificationMethod
}

export async function deleteNotificationMethod(uuid: string, abortSignal?: AbortSignal): Promise<void> {
  return await makeAuthenticatedClient().delete(
    'api/v1/alert_methods/' + uuid + '/', {
      signal: abortSignal
    });
}

export interface TaskPageFetchOptions extends PageFetchWithGroupIdAndRunEnvironmentOptions {
  isService?: boolean;
  statuses?: string[];
  otherParams?: any;
}

export async function fetchTasks(opts?: TaskPageFetchOptions)
  : Promise<ResultsPage<TaskImpl>> {
  opts = opts ?? {};

  const {
    abortSignal
  } = opts;

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);

  if (opts.isService !== undefined) {
    params['is_service'] = '' + opts.isService;
  }

  if (opts.statuses) {
    params['latest_task_execution__status'] = opts.statuses.join(',');
  }

  params['omit'] = 'current_service_info,execution_method_capability_details,infrastructure_settings,scheduling_settings,service_settings,input_value_schema,alert_methods,links';

  if (opts.otherParams) {
    Object.assign(params, opts.otherParams);
  }

  const response = await makeAuthenticatedClient().get(
    'api/v1/tasks/', {
      signal: abortSignal,
      params
     });

  const page =  response.data as ResultsPage<Task>;

  return plainToInstance(ResultsPageImpl, {
    count: page.count,
    results: plainToInstance(TaskImpl, page.results)
  });
}

export async function fetchTask(uuid: string,
    abortSignal?: AbortSignal): Promise<TaskImpl> {
  const response = await makeAuthenticatedClient().get(
    'api/v1/tasks/' + encodeURIComponent(uuid) + '/', {
      signal: abortSignal
    });
  return plainToInstance(TaskImpl, response.data);
}

export async function updateTask(uuid: string, data: any,
    abortSignal?: AbortSignal): Promise<TaskImpl> {
  const response = await makeAuthenticatedClient().patch(
    'api/v1/tasks/' + encodeURIComponent(uuid) + '/',
    data, {
      signal: abortSignal
    });
  return plainToInstance(TaskImpl, response.data);
}

export interface TaskExecutionPageFetchOptions
extends PageFetchWithGroupIdAndRunEnvironmentOptions {
  taskUuid?: string;
  statuses?: string[];
}

export async function fetchTaskExecutions(opts?: TaskExecutionPageFetchOptions): Promise<ResultsPage<TaskExecution>> {
  opts = opts ?? {};

  const {
    taskUuid,
    statuses,
    abortSignal
  } = opts;

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);

  if (taskUuid) {
    params.task__uuid = taskUuid;
  }

  if (statuses) {
    params['status__in'] = statuses.join(',');
  }

  params['omit'] = 'debug_log_tail,environment_variables_overrides,execution_method,execution_method_details,infrastructure_settings';

  console.log('fetchTaskExecutions', params);

  const response = await makeAuthenticatedClient().get(
    'api/v1/task_executions/', {
      signal: abortSignal,
      params
    });

  return response.data as ResultsPage<TaskExecution>;
}

export async function fetchTaskExecution(uuid: string,
    abortSignal?: AbortSignal): Promise<TaskExecution> {
  const response = await makeAuthenticatedClient().get(
    'api/v1/task_executions/' + encodeURIComponent(uuid) + '/', {
      signal: abortSignal
    });
  return response.data as TaskExecution;
}

export async function startTaskExecution(taskUuid: string,
    executionProps?: any, abortSignal?: AbortSignal): Promise<TaskExecution> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/task_executions/',
    Object.assign(executionProps ?? {}, {
       task: {
         uuid: taskUuid
       },
       status: C.TASK_EXECUTION_STATUS_MANUALLY_STARTED
    }, {
      signal: abortSignal
    })
  );
  return response.data as TaskExecution;
}

export async function stopTaskExecution(uuid: string,
    abortSignal?: AbortSignal): Promise<TaskExecution> {
  const response = await makeAuthenticatedClient().patch(
    'api/v1/task_executions/' + encodeURIComponent(uuid) + '/',
    {
      status: C.TASK_EXECUTION_STATUS_STOPPING
    }, {
      signal: abortSignal
    }
  );
  return response.data as TaskExecution;
}

const DEFAULT_RUN_ENVIRONMENT_PARAMS = {
  omit: 'aws_account_id,aws_default_region,execution_method_capabilities'
}

export async function fetchRunEnvironments(opts? : PageFetchWithGroupIdOptions):
  Promise<ResultsPage<RunEnvironment>> {
  opts = opts ?? {};

  const {
    abortSignal
  } = opts;

  const params = makePageFetchWithGroupParams(opts);
  const response = await makeAuthenticatedClient().get(
    'api/v1/run_environments/', {
      signal: abortSignal,
      params: Object.assign(DEFAULT_RUN_ENVIRONMENT_PARAMS, params)
    });
  return response.data as ResultsPage<RunEnvironment>;
}

export async function fetchRunEnvironment(uuid: string,
    abortSignal?: AbortSignal) {
  const response = await makeAuthenticatedClient().get(
    'api/v1/run_environments/' + encodeURIComponent(uuid) + '/', {
      signal: abortSignal,
      params: DEFAULT_RUN_ENVIRONMENT_PARAMS
    });
  return response.data as RunEnvironment;
}

export async function deleteRunEnvironment(uuid: string,
    abortSignal?: AbortSignal): Promise<void> {
  return await makeAuthenticatedClient().delete(
    'api/v1/run_environments/' + uuid + '/', {
      signal: abortSignal
    });
}

export async function cloneRunEnvironment(uuid: string, attributes: any,
    abortSignal?: AbortSignal): Promise<RunEnvironment> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/run_environments/' + uuid + '/clone/', attributes, {
      signal: abortSignal
    });
  return response.data as RunEnvironment
}

export async function fetchPagerDutyProfiles(
  opts? : PageFetchWithGroupIdAndScopedRunEnvironmentOptions): Promise<ResultsPage<PagerDutyProfile>> {
  opts = opts ?? {};

  const {
    abortSignal
  } = opts;

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);

  const response = await makeAuthenticatedClient().get(
    'api/v1/pagerduty_profiles/', {
      signal: abortSignal,
      params
    });

  return response.data as ResultsPage<PagerDutyProfile>;
}

export async function fetchPagerDutyProfile(uuid: string,
    abortSignal?: AbortSignal): Promise<PagerDutyProfile> {
  const response = await makeAuthenticatedClient().get(
    `api/v1/pagerduty_profiles/${uuid}/`, {
      signal: abortSignal
    });
  return response.data as PagerDutyProfile;
}

export async function savePagerDutyProfile(uuid: string, values: any,
    abortSignal?: AbortSignal) : Promise<PagerDutyProfile> {
  const client = makeAuthenticatedClient();

  const response = await ((!uuid || (uuid === 'new')) ? client.post(
    'api/v1/pagerduty_profiles/', values, {
      signal: abortSignal
    }
  ) : client.patch(`api/v1/pagerduty_profiles/${uuid}/`, values, {
      signal: abortSignal
    }
  ));

  return response.data as PagerDutyProfile;
}

export async function clonePagerDutyProfile(uuid: string, attributes?: any, abortSignal?: AbortSignal): Promise<PagerDutyProfile> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/pagerduty_profiles/' + uuid + '/clone/', attributes || {}, {
        signal: abortSignal
    });
  return response.data as PagerDutyProfile
}

export async function deletePagerDutyProfile(uuid: string, abortSignal?: AbortSignal): Promise<void> {
  return await makeAuthenticatedClient().delete(
    'api/v1/pagerduty_profiles/' + uuid + '/', {
      signal: abortSignal
    });
}

export async function fetchEmailNotificationProfiles(
  opts? : PageFetchWithGroupIdAndScopedRunEnvironmentOptions): Promise<ResultsPage<EmailNotificationProfile>> {
  opts = opts ?? {};

  const {
    abortSignal
  } = opts;

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);
  const response = await makeAuthenticatedClient().get(
    'api/v1/email_notification_profiles/', {
    signal: abortSignal,
    params
  });
  return response.data as ResultsPage<EmailNotificationProfile>;
}

export async function fetchEmailNotificationProfile(uuid: string,
    abortSignal?: AbortSignal): Promise<EmailNotificationProfile> {
  const response = await makeAuthenticatedClient().get(
    `api/v1/email_notification_profiles/${uuid}/`, {
      signal: abortSignal
    });
  return response.data as EmailNotificationProfile;
}

export async function saveEmailNotificationProfile(uuid: string, values: any,
    abortSignal?: AbortSignal) : Promise<EmailNotificationProfile> {
  const client = makeAuthenticatedClient();

  const response = await ((!uuid || (uuid === 'new')) ? client.post(
    'api/v1/email_notification_profiles/',
    values, {
      signal: abortSignal
    }
  ) : client.patch(`api/v1/email_notification_profiles/${uuid}/`, values));

  return response.data as EmailNotificationProfile;
}

export async function cloneEmailNotificationProfile(uuid: string, attributes?: any, abortSignal?: AbortSignal): Promise<EmailNotificationProfile> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/email_notification_profiles/' + uuid + '/clone/', attributes || {}, {
        signal: abortSignal
    });
  return response.data as EmailNotificationProfile
}

export async function deleteEmailNotificationProfile(uuid: string, abortSignal?: AbortSignal): Promise<void> {
  return await makeAuthenticatedClient().delete(
    'api/v1/email_notification_profiles/' + uuid + '/', {
      signal: abortSignal
    });
}

export function makeErrorElement(e: any, fallbackText: string = 'An error occurred'): any {
  const data = e?.response?.data;
  if (data) {
    return (
      <div>
        <i className="fas fa-times" />&nbsp;
        {e.message}
        <div>
          {
            (typeof data === 'string') ?
            data :
            (typeof data === 'object') ?
            <ul>
              {
                Object.keys(data).map(k => {
                  return (
                    <li key={k}>
                      {k}{data[k] && ':'}
                      {
                        data[k] ? (
                          Array.isArray(data[k])? (
                            <ul>
                              {
                                Object.keys(data[k]).map(j => {
                                  return <li key={j}>{data[k][j]}</li>;
                                })
                              }
                            </ul>
                          ) : data[k]
                        ) : null
                      }
                    </li>
                  );
                })
              }
            </ul> :
            null
          }
        </div>
      </div>
    );
  } else {
    return fallbackText;
  }
}