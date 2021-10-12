import _ from 'lodash';

import { WorkflowExecution } from '../types/domain_types';
import * as C from './constants';

export function shouldRefreshWorkflowExecution(workflowExecution: WorkflowExecution): boolean {
  if ((workflowExecution.status === C.WORKFLOW_EXECUTION_STATUS_MANUALLY_STARTED) ||
      (workflowExecution.status === C.WORKFLOW_EXECUTION_STATUS_RUNNING)) {
    return true;
  }

  return !!_.find(workflowExecution.workflow_task_instance_executions, wptie => {
    if (!wptie.is_latest) {
      return false;
    }
    const ps = wptie.task_execution.status;
    return ((ps === C.TASK_EXECUTION_STATUS_MANUALLY_STARTED) ||
            (ps === C.TASK_EXECUTION_STATUS_RUNNING));
  });
}

export function makeCloneName(originalName: string) {
  const m = /(.+) \(Copy (\d+)\)/.exec(originalName)

  if (m) {
    return m[1] + ' (Copy ' + (parseInt(m[2]) + 1) + ')';
  } else {
    return originalName + " (Copy 1)"
  }
}