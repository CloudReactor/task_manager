import {
  plainToClass
} from 'class-transformer';

import { CancelToken } from 'axios';

import { makeAuthenticatedClient } from '../axios_config';

import React from 'react'

import {
  Group, User, Invitation
} from '../types/website_types';

import {
  AlertMethod,
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
  cancelToken?: CancelToken;
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
  runEnvironmentUuid?: string | null;
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

  const runEnvironmentUuid = pageFetchOptions?.runEnvironmentUuid ?? defaultOptions?.runEnvironmentUuid;

  if (runEnvironmentUuid) {
    params['run_environment__uuid'] = '' + runEnvironmentUuid;
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
  //{ value: 10, text: 10 },
  { value: 25, text: 25 },
  { value: 50, text: 50 },
  { value: 100, text: 100 }
];

export async function fetchCurrentUser(fetchOptions?: FetchOptions): Promise<User> {
  const {
    cancelToken
  } = fetchOptions ?? {};

  const response = await makeAuthenticatedClient().get(
    'auth/users/me/', {
      cancelToken
    });
  return response.data as User;
}

export async function fetchUsers(opts? : PageFetchWithGroupIdOptions):
    Promise<ResultsPage<User>> {
  opts = opts ?? {};

  const {
    cancelToken
  } = opts;

  const params = makePageFetchWithGroupParams(opts);

  params.group__id = params.created_by_group__id;
  delete params.created_by_group__id;

  const response = await makeAuthenticatedClient().get(
    'api/v1/users/', {
      cancelToken,
      params
    });

  return response.data as ResultsPage<User>;
}

export async function fetchGroup(id: number): Promise<Group> {
  const response = await makeAuthenticatedClient().get(
    'api/v1/groups/' + id + '/');
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

export async function fetchApiKey(uuid: string) {
  const response = await makeAuthenticatedClient().get(
    `api/v1/api_keys/${uuid}/`);
  return response.data as ApiKey;
}

export async function saveApiKey(apiKey: any) : Promise<ApiKey> {
  const client = makeAuthenticatedClient();
  const response = await (apiKey.uuid ? client.patch(
    'api/v1/api_keys/' + encodeURIComponent(apiKey.uuid) + '/',
    apiKey
  ) : client.post('api/v1/api_keys/', apiKey));

  return response.data as ApiKey;
}

export async function fetchApiKeys(opts? : PageFetchWithGroupIdOptions):
   Promise<ResultsPage<ApiKey>> {
  opts = opts ?? {};

  const {
    cancelToken
  } = opts;

  const params = makePageFetchWithGroupParams(opts);

  params.group__id = params.created_by_group__id;
  delete params.created_by_group__id;

  const response = await makeAuthenticatedClient().get(
    'api/v1/api_keys/', {
      cancelToken,
      params
    });

  return response.data as ResultsPage<ApiKey>;
}

export async function deleteApiKey(uuid: string): Promise<void> {
  const client = makeAuthenticatedClient();
  await client.delete(
    'api/v1/api_keys/' + encodeURIComponent(uuid) + '/');
}

export async function fetchWorkflowSummaries(opts?: PageFetchWithGroupIdAndRunEnvironmentOptions)
  : Promise<ResultsPage<WorkflowSummary>> {
  opts = opts ?? {};

  const {
    cancelToken
  } = opts;

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);

  const response = await makeAuthenticatedClient().get(
    'api/v1/workflows/', {
      cancelToken,
      params
    });

  return response.data as ResultsPage<WorkflowSummary>;
}

export async function fetchWorkflow(uuid: string): Promise<Workflow> {
  const response = await makeAuthenticatedClient().get(
      'api/v1/workflows/' + encodeURIComponent(uuid) + '/');
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

export async function cloneWorkflow(uuid: string, attributes: any): Promise<Workflow> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/workflows/' + uuid + '/clone/', attributes);
  return response.data as Workflow;
}

export async function fetchWorkflowExecutionSummaries(
  workflowUuid?: string,
  sortBy?: string,
  descending?: boolean,
  offset?: number,
  maxResults?: number,
  cancelToken?: CancelToken
) : Promise<ResultsPage<WorkflowExecutionSummary>> {

  descending = descending || false;
  offset = offset || 0;
  maxResults = maxResults || UIC.DEFAULT_PAGE_SIZE;

  let ordering = sortBy || 'started_at';
  ordering = descending ? `-${ordering}` : ordering;

  const params: any = {
    ordering,
    offset,
    limit: maxResults
  }

  if (workflowUuid) {
    params.workflow__uuid = workflowUuid;
  }

  const response = await makeAuthenticatedClient().get('api/v1/workflow_executions/', {
    cancelToken,
    params
  });

  return response.data as ResultsPage<WorkflowExecutionSummary>;
}

export async function fetchWorkflowExecution(uuid: string): Promise<WorkflowExecution> {
  const response = await makeAuthenticatedClient().get(
      'api/v1/workflow_executions/' + encodeURIComponent(uuid) + '/');
  return response.data as WorkflowExecution;
}

export async function startWorkflowExecution(workflowUuid: string): Promise<WorkflowExecution> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/workflow_executions/',
    {
       workflow: {
         uuid: workflowUuid
       },
       status: C.WORKFLOW_EXECUTION_STATUS_MANUALLY_STARTED
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
    workflowExecutionUuid: string): Promise<WorkflowExecution> {

  const response = await makeAuthenticatedClient().post(
    'api/v1/workflow_executions/' + workflowExecutionUuid + '/retry/'
  );
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

export async function fetchAlertMethods(
  opts? :  PageFetchWithGroupIdAndScopedRunEnvironmentOptions): Promise<ResultsPage<AlertMethod>> {
  opts = opts ?? {};

  const {
    cancelToken
  } = opts;

  const params = makePageFetchWithGroupAndScopedRunEnvironmentParams(opts);
  const response = await makeAuthenticatedClient().get(
    'api/v1/alert_methods/', {
      cancelToken,
      params
    });

  return response.data as ResultsPage<AlertMethod>;
}

export async function fetchAlertMethod(uuid: string, cancelToken?: CancelToken) {
  const response = await makeAuthenticatedClient().get(
    `api/v1/alert_methods/${uuid}/`, {
      cancelToken
    });
  return response.data as AlertMethod;
}

export async function saveAlertMethod(uuid: string, values: any,
    cancelToken?: CancelToken) : Promise<AlertMethod> {
  // remove name & url -- only use UUID to associate selected PD profile with this AlertMethod
  delete values.method_details.profile.name;
  delete values.method_details.profile.url;

  const client = makeAuthenticatedClient();

  const response = await ((!uuid || (uuid === 'new')) ? client.post(
    'api/v1/alert_methods/', values, {
      cancelToken
    }
  ) : client.patch(`api/v1/alert_methods/${uuid}/`, values, {
      cancelToken
    })
  );

  return response.data;
}

export async function cloneAlertMethod(uuid: string, attributes?: any, cancelToken?: CancelToken): Promise<AlertMethod> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/alert_methods/' + uuid + '/clone/', attributes || {}, {
        cancelToken
    });
  return response.data as AlertMethod
}

export async function deleteAlertMethod(uuid: string, cancelToken?: CancelToken): Promise<void> {
  return await makeAuthenticatedClient().delete(
    'api/v1/alert_methods/' + uuid + '/', {
      cancelToken
    });
}

export interface TaskPageFetchOptions extends PageFetchWithGroupIdOptions {
  selectedRunEnvironmentUuid?: string;
  isService?: boolean;
  otherParams?: any;
}

export async function fetchTasks(opts?: TaskPageFetchOptions)
  : Promise<ResultsPage<TaskImpl>> {
  opts = opts ?? {};

  const {
    cancelToken
  } = opts;

  const params = makePageFetchWithGroupParams(opts);

  if (opts.isService !== undefined) {
    params['is_service'] = '' + opts.isService;
  }

  if (opts.selectedRunEnvironmentUuid) {
    params['run_environment__uuid'] = opts.selectedRunEnvironmentUuid;
  }

  params['omit'] = 'execution_method_capability.details,alert_methods,links';

  if (opts.otherParams) {
    Object.assign(params, opts.otherParams);
  }

  const response = await makeAuthenticatedClient().get(
    'api/v1/tasks/', {
      cancelToken,
      params
     });

  const page =  response.data as ResultsPage<Task>;

  return plainToClass(ResultsPageImpl, {
    count: page.count,
    results:  plainToClass(TaskImpl, page.results)
  });
}

export async function fetchTask(uuid: string,
    cancelToken?: CancelToken): Promise<TaskImpl> {
  const response = await makeAuthenticatedClient().get(
    'api/v1/tasks/' + encodeURIComponent(uuid) + '/', {
      cancelToken
    });
  return plainToClass(TaskImpl, response.data);
}

export async function updateTask(uuid: string, data: any,
    cancelToken?: CancelToken): Promise<TaskImpl> {
  const response = await makeAuthenticatedClient().patch(
    'api/v1/tasks/' + encodeURIComponent(uuid) + '/',
    data, {
      cancelToken
    });
  return plainToClass(TaskImpl, response.data);
}

export interface TaskExecutionPageFetchOptions
extends PageFetchWithGroupIdAndRunEnvironmentOptions {
  taskUuid?: string;
}

export async function fetchTaskExecutions(opts?: TaskExecutionPageFetchOptions): Promise<ResultsPage<TaskExecution>> {
  opts = opts ?? {};

  const {
    cancelToken
  } = opts;

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);

  if (opts.taskUuid) {
    params.task__uuid = opts.taskUuid;
  }

  const response = await makeAuthenticatedClient().get(
    'api/v1/task_executions/', {
      cancelToken,
      params
    });

  return response.data as ResultsPage<TaskExecution>;
}

export async function fetchTaskExecution(uuid: string,
    cancelToken?: CancelToken): Promise<TaskExecution> {
  const response = await makeAuthenticatedClient().get(
    'api/v1/task_executions/' + encodeURIComponent(uuid) + '/', {
      cancelToken
    });
  return response.data as TaskExecution;
}

export async function startTaskExecution(taskUuid: string,
    executionProps?: any, cancelToken?: CancelToken): Promise<TaskExecution> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/task_executions/',
    Object.assign(executionProps ?? {}, {
       task: {
         uuid: taskUuid
       },
       status: C.TASK_EXECUTION_STATUS_MANUALLY_STARTED
    }, {
      cancelToken
    })
  );
  return response.data as TaskExecution;
}

export async function stopTaskExecution(uuid: string,
    cancelToken?: CancelToken): Promise<TaskExecution> {
  const response = await makeAuthenticatedClient().patch(
    'api/v1/task_executions/' + encodeURIComponent(uuid) + '/',
    {
      status: C.TASK_EXECUTION_STATUS_STOPPING
    }, {
      cancelToken
    }
  );
  return response.data as TaskExecution;
}

export async function fetchRunEnvironments(opts? : PageFetchWithGroupIdOptions):
  Promise<ResultsPage<RunEnvironment>> {
  opts = opts ?? {};

  const {
    cancelToken
  } = opts;

  const params = makePageFetchWithGroupParams(opts);
  const response = await makeAuthenticatedClient().get(
    'api/v1/run_environments/', {
      cancelToken,
      params
    });
  return response.data as ResultsPage<RunEnvironment>;
}

export async function fetchRunEnvironment(uuid: string,
    cancelToken?: CancelToken) {
  const response = await makeAuthenticatedClient().get(
    'api/v1/run_environments/' + encodeURIComponent(uuid) + '/', {
      cancelToken
    });
  return response.data as RunEnvironment;
}

export async function deleteRunEnvironment(uuid: string,
    cancelToken?: CancelToken): Promise<void> {
  return await makeAuthenticatedClient().delete(
    'api/v1/run_environments/' + uuid + '/', {
      cancelToken
    });
}

export async function cloneRunEnvironment(uuid: string, attributes: any,
    cancelToken?: CancelToken): Promise<RunEnvironment> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/run_environments/' + uuid + '/clone/', attributes, {
      cancelToken
    });
  return response.data as RunEnvironment
}

export async function fetchPagerDutyProfiles(
  opts? : PageFetchWithGroupIdAndRunEnvironmentOptions): Promise<ResultsPage<PagerDutyProfile>> {
  opts = opts ?? {};

  const {
    cancelToken
  } = opts;

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);

  const response = await makeAuthenticatedClient().get(
    'api/v1/pagerduty_profiles/', {
      cancelToken,
      params
    });

  return response.data as ResultsPage<PagerDutyProfile>;
}

export async function fetchPagerDutyProfile(uuid: string,
    cancelToken?: CancelToken): Promise<PagerDutyProfile> {
  const response = await makeAuthenticatedClient().get(
    `api/v1/pagerduty_profiles/${uuid}/`, {
      cancelToken
    });
  return response.data as PagerDutyProfile;
}

export async function savePagerDutyProfile(uuid: string, values: any,
    cancelToken?: CancelToken) : Promise<PagerDutyProfile> {
  const client = makeAuthenticatedClient();

  const response = await ((!uuid || (uuid === 'new')) ? client.post(
    'api/v1/pagerduty_profiles/', values, {
      cancelToken
    }
  ) : client.patch(`api/v1/pagerduty_profiles/${uuid}/`, values, {
      cancelToken
    }
  ));

  return response.data as PagerDutyProfile;
}

export async function clonePagerDutyProfile(uuid: string, attributes?: any, cancelToken?: CancelToken): Promise<PagerDutyProfile> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/pagerduty_profiles/' + uuid + '/clone/', attributes || {}, {
        cancelToken
    });
  return response.data as PagerDutyProfile
}

export async function deletePagerDutyProfile(uuid: string, cancelToken?: CancelToken): Promise<void> {
  return await makeAuthenticatedClient().delete(
    'api/v1/pagerduty_profiles/' + uuid + '/', {
      cancelToken
    });
}

export async function fetchEmailNotificationProfiles(
  opts? : PageFetchWithGroupIdAndRunEnvironmentOptions): Promise<ResultsPage<EmailNotificationProfile>> {
  opts = opts ?? {};

  const {
    cancelToken
  } = opts;

  const params = makePageFetchWithGroupAndRunEnvironmentParams(opts);
  const response = await makeAuthenticatedClient().get(
    'api/v1/email_notification_profiles/', {
    cancelToken,
    params
  });
  return response.data as ResultsPage<EmailNotificationProfile>;
}

export async function fetchEmailNotificationProfile(uuid: string,
    cancelToken?: CancelToken): Promise<EmailNotificationProfile> {
  const response = await makeAuthenticatedClient().get(
    `api/v1/email_notification_profiles/${uuid}/`, {
      cancelToken
    });
  return response.data as EmailNotificationProfile;
}

export async function saveEmailNotificationProfile(uuid: string, values: any,
    cancelToken?: CancelToken) : Promise<EmailNotificationProfile> {
  const client = makeAuthenticatedClient();

  const response = await ((!uuid || (uuid === 'new')) ? client.post(
    'api/v1/email_notification_profiles/',
    values, {
      cancelToken
    }
  ) : client.patch(`api/v1/email_notification_profiles/${uuid}/`, values));

  return response.data as EmailNotificationProfile;
}

export async function cloneEmailNotificationProfile(uuid: string, attributes?: any, cancelToken?: CancelToken): Promise<EmailNotificationProfile> {
  const response = await makeAuthenticatedClient().post(
    'api/v1/email_notification_profiles/' + uuid + '/clone/', attributes || {}, {
        cancelToken
    });
  return response.data as EmailNotificationProfile
}

export async function deleteEmailNotificationProfile(uuid: string, cancelToken?: CancelToken): Promise<void> {
  return await makeAuthenticatedClient().delete(
    'api/v1/email_notification_profiles/' + uuid + '/', {
      cancelToken
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