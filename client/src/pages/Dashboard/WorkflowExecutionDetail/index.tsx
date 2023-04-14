import React, { useContext, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { WorkflowExecution } from '../../../types/domain_types';

import { GlobalContext, accessLevelForCurrentGroup } from '../../../context/GlobalContext';

import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import {
  fetchWorkflowExecution, retryWorkflowExecution, stopWorkflowExecution
} from '../../../utils/api'

import {
  Alert
} from 'react-bootstrap/'

import * as UIC from '../../../utils/ui_constants';
import { BootstrapVariant } from '../../../types/ui_types';
import AccessDenied from '../../../components/AccessDenied';
import BreadcrumbBar from "../../../components/BreadcrumbBar/BreadcrumbBar";
import Loading from '../../../components/Loading';
import WorkflowExecutionDetailsTable from '../../../components/WorkflowExecutionDetails/WorkflowExecutionDetailsTable';
import WorkflowExecutionDiagram from '../../../components/WorkflowExecutionDetails/WorkflowExecutionDiagram';
import {
  WORKFLOW_EXECUTION_STATUSES_IN_PROGRESS
} from '../../../utils/constants';
import {shouldRefreshWorkflowExecution} from '../../../utils/domain_utils';
import ActionButton from '../../../components/common/ActionButton';
import styles from './index.module.scss';
import _ from 'lodash';
import { catchableToString } from '../../../utils';


type PathParamsType = {
  uuid: string;
};

const WorkflowExecutionDetail = (props: AbortSignalProps) => {
  const {
    abortSignal
  } = props;

  const context = useContext(GlobalContext);

  const accessLevel = accessLevelForCurrentGroup(context);

  if (!accessLevel) {
    return <AccessDenied />;
  }

  const [isLoading, setLoading] = useState(false);
  const [loadErrorMessage, setLoadErrorMessage] = useState<string | null>(null);
  const [flashBody, setFlashBody] = useState<string | null>(null);
  const [flashAlertVariant, setFlashAlertVariant] = useState<BootstrapVariant>('info');
  const [workflowExecution, setWorkflowExecution] = useState<WorkflowExecution | null>(null);
  const [isStopping, setStopping] = useState(false);
  const [isRetryRequested, setRetryRequested] = useState(false);
  const [selfInterval, setSelfInterval] = useState<any>(null);

  const {
    uuid
  }  = useParams<PathParamsType>();

  const setupRefresh = (execution: WorkflowExecution) => {
    if (execution && shouldRefreshWorkflowExecution(execution)) {
      if (!selfInterval) {
        const updatedInterval = setInterval(fetchExecutionDetails,
          UIC.TASK_REFRESH_INTERVAL_MILLIS);
        setSelfInterval(updatedInterval);
      }
    } else if (selfInterval) {
      clearInterval(selfInterval)
      setSelfInterval(null);
    }
  }

  const fetchExecutionDetails = async () => {
    setLoadErrorMessage(null);
    setLoading(true);
    try {
      const execution = await fetchWorkflowExecution(uuid, abortSignal);
      setWorkflowExecution(execution);
      setupRefresh(execution);
      setFlashBody(null);
      return execution;
    } catch (ex) {
      const message = "Failed to fetch WorkflowExecution: " + catchableToString(ex);
      setLoadErrorMessage(message);
      setFlashBody(message);
      setFlashAlertVariant('danger');
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    document.title = 'Task Execution Details';
    if (!isLoading && !workflowExecution && !loadErrorMessage) {
      fetchExecutionDetails();
    }

    return () => {
      if (selfInterval) {
        clearInterval(selfInterval);
      }
    };
  });

  if (!workflowExecution) {
    return <Loading />;
  }

  const workflowLink = (
    <Link to={`/workflows/${workflowExecution.workflow.uuid}`}>
      {workflowExecution.workflow.name}
    </Link>
  );

  const inProgress = WORKFLOW_EXECUTION_STATUSES_IN_PROGRESS.includes(workflowExecution.status);

  const handleWorkflowExecutionUpdated = async (workflowExecutionUuid: string, execution?: WorkflowExecution) => {
    if (execution) {
      setWorkflowExecution(execution);
      setupRefresh(execution);
    } else {
      await fetchExecutionDetails();
    }
  }

  const handleActionRequested = (action: string | undefined, cbData: any) => {
    if (!workflowExecution) {
      return;
    }

    switch (action) {
      case 'stop':
        setStopping(true);
        stopWorkflowExecution(uuid).then(we => {
          setFlashBody('Stopped Workflow Execution successfully.');
          setFlashAlertVariant('info');
          setWorkflowExecution(we);
        }).catch (reason => {
          const message = catchableToString(reason);
          setFlashBody(message);
        }).finally(() => setStopping(false));
        break;

      case 'retry':
        setRetryRequested(true);

        retryWorkflowExecution(uuid).then(we => {
          setWorkflowExecution(we);
          setFlashBody('Restarted Workflow Execution successfully.');
          setFlashAlertVariant('info');
        }).catch (reason => {
          const message = catchableToString(reason);
          setFlashBody(message);
        }).finally(() => setRetryRequested(false));
        break;

      default:
        console.error(`Unknown action ${action}`);
        break;
    }
  }


  return (
    <div className={styles.container}>
      <BreadcrumbBar
        rootUrl="/workflows" rootLabel="Workflows"
        firstLevel={workflowLink}
        secondLevel={'Execution ' + workflowExecution.uuid}
      />
      {
        (flashBody && !isLoading && !isStopping && !isRetryRequested) &&
        <Alert
          variant={flashAlertVariant || 'success'}
          onClose={() => {
            setFlashBody(null);
          }}
          dismissible>
          {flashBody}
        </Alert>
      }

      <div>
        <ActionButton action="stop" faIconName="stop" label="Stop"
          onActionRequested={handleActionRequested}
          inProgress={isStopping} inProgressLabel="Stopping"
          disabled={!inProgress}
        />
        <ActionButton action="retry" faIconName="redo" label="Retry"
          onActionRequested={handleActionRequested}
          inProgress={isRetryRequested} inProgressLabel="Retrying"
          disabled={inProgress}
        />
      </div>
      <WorkflowExecutionDetailsTable workflowExecution={workflowExecution} />
      <WorkflowExecutionDiagram workflowExecution={workflowExecution}
        onWorkflowExecutionUpdated={handleWorkflowExecutionUpdated}/>
    </div>
  );
}

export default abortableHoc(WorkflowExecutionDetail);
