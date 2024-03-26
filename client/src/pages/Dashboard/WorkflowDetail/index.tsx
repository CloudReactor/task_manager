import { AxiosError, isCancel } from 'axios';

import {makeNewWorkflow, Workflow, WorkflowExecution} from '../../../types/domain_types';
import { catchableToString } from '../../../utils';
import {
  cloneWorkflow,
  deleteWorkflow,
  fetchWorkflow,
  fetchWorkflowExecution,
  retryWorkflowExecution,
  startWorkflowExecution
} from '../../../utils/api';

import * as C from '../../../utils/constants';

import { shouldRefreshWorkflowExecution } from '../../../utils/domain_utils';

import React, { useContext, useEffect, useState } from 'react';
import {
  useNavigate, useParams, useSearchParams
} from 'react-router-dom';

import {
  Alert,
  ButtonToolbar,
  Form, FormControl, FormGroup, FormLabel,
} from 'react-bootstrap';

import * as UIC from '../../../utils/ui_constants';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import ActionButton from '../../../components/common/ActionButton';
import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import ConfirmationModal from '../../../components/common/ConfirmationModal';
import Loading from '../../../components/Loading';
import AccessDenied from '../../../components/AccessDenied';
import WorkflowEditor from './WorkflowEditor';
import styles from './index.module.scss';

import _ from 'lodash';

type PathParamsType = {
  uuid: string;
};

type Props = AbortSignalProps;

const WorkflowDetail = ({
  abortSignal
}: Props) => {
  const context = useContext(GlobalContext);

  const accessLevel = accessLevelForCurrentGroup(context);

  if (!accessLevel) {
    return <AccessDenied />;
  }

  const {
    uuid
  } = useParams<PathParamsType>();

  if (!uuid) {
    return <div>Invalid UUID</div>;
  }

  const [workflow, setWorkflow] = useState<Workflow | null>(
    (uuid == 'new') ? makeNewWorkflow() : null);
  const [isWorkflowLoading, setWorkflowLoading] = useState(false);
  const [loadErrorMessage, setLoadErrorMessage] = useState<string | null>(null);
  const [workflowExecution, setWorkflowExecution] = useState<WorkflowExecution | null>(null);
  const [isStarting, setStarting] = useState(false);
  const [isRetryRequested, setRetryRequested] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [shouldShowCloneModal, setShouldShowCloneModal] = useState(false);
  const [isCloning, setCloning] = useState(false);
  const [cloneName, setCloneName] = useState<string | null>(null);
  const [cloneErrorMessage, setCloneErrorMessage] = useState<string | null>(null);
  const [shouldShowDeletionModal, setShouldShowDeletionModal] = useState(false);
  const [isDeleting, setDeleting] = useState(false);
  const [deletionErrorMessage, setDeletionErrorMessage] = useState<string | null>(null);
  const [selfInterval, setSelfInterval] = useState<any>(null);

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedTab = searchParams.get('tab') ?? 'graph';

  console.debug('selectedTab:', selectedTab);

  const handleLatestWorkflowExecutionUpdated = (execution: WorkflowExecution | null) => {
    setWorkflowExecution(execution);

    if (execution && shouldRefreshWorkflowExecution(execution)) {
      if (!selfInterval) {
        setSelfInterval(setInterval(loadLatestWorkflowExecution,
            UIC.TASK_REFRESH_INTERVAL_MILLIS));
      }
    } else {
      if (selfInterval) {
        clearInterval(selfInterval);
        setSelfInterval(null);
      }
    }
  };

  const handleWorkflowExecutionUpdated = (execution: WorkflowExecution) => {
    if (!workflow) {
      return;
    }

    const latestWorkflowExecution = workflow.latest_workflow_execution;

    if (latestWorkflowExecution && (latestWorkflowExecution.uuid === execution.uuid)) {
      handleLatestWorkflowExecutionUpdated(execution);
    }
  }

  const handleTabChange = (selectedTab: string | null) => {
    const value = selectedTab?.toLowerCase() || 'graph';
    setSearchParams(oldSearchParams => {
      oldSearchParams.set('tab', value);
      return oldSearchParams;
    }, { replace: true });
  };

  const loadLatestWorkflowExecution = async () => {
    let workflowExecution: WorkflowExecution | null = null;

    if (workflow?.latest_workflow_execution) {
      workflowExecution = await fetchWorkflowExecution(
        workflow.latest_workflow_execution.uuid, abortSignal);
    }

    handleLatestWorkflowExecutionUpdated(workflowExecution);

    return workflowExecution;
  };

  const updateTitle = (workflow: Workflow) => {
    document.title = `CloudReactor - Workflow ${workflow.name}`;
  }

  const loadWorkflowDetails = async () => {
    try {
      const fetchedWorkflow = await fetchWorkflow(uuid, abortSignal);

      setWorkflow(fetchedWorkflow);
      setLoadErrorMessage(null);
    } catch (err) {
      let updatedErrorMessage = 'An error occurred loading this Workflow.'

      if ((err instanceof AxiosError) && (err.response?.status === 404)) {
        updatedErrorMessage = "Can't find this Workflow. Perhaps it was removed?"
      }

      setLoadErrorMessage(updatedErrorMessage);
    } finally {
      setWorkflowLoading(false);
    }

    await loadLatestWorkflowExecution();
  };

  const handleActionError = (action: string, cbData: any, errorMessage: string) => {
    setErrorMessage(errorMessage);
  };


  const handleWorkflowChanged = (updatedWorkflow: Workflow) => {
    const oldWorkflow = workflow;

    setWorkflow(updatedWorkflow);
    updateTitle(updatedWorkflow);

    if (!oldWorkflow?.uuid && updatedWorkflow.uuid) {
      navigate('/workflows/' + encodeURIComponent(updatedWorkflow.uuid),
        { replace: true });
    }
  }

  const handleActionRequested = async (action: string | undefined, cbData: any) => {
    switch (action) {
      case 'start':
        setStarting(true);
        try {
          const startedExecution = await startWorkflowExecution(cbData.uuid,
            abortSignal);
          navigate('/workflow_executions/' +
              encodeURIComponent(startedExecution.uuid));
        } catch (err) {
          if (isCancel(err)) {
            console.log("Request canceled: " + err.message);
            return;
          }
          console.dir(err);

          setErrorMessage('Failed to start Workflow: '  +
            catchableToString(err));
        } finally {
          setStarting(false);
        }
        break;

      case 'retry':
        setRetryRequested(true);
        try {
          const workflowExecution = await retryWorkflowExecution(cbData.uuid,
            abortSignal);
          navigate('/workflow_executions/' +
              encodeURIComponent(workflowExecution.uuid));
        } catch (err) {
          if (isCancel(err)) {
            console.log("Request canceled: " + err.message);
            return;
          }
          console.dir(err);

          setErrorMessage('Failed to retry Workflow Execution: ' +
            catchableToString(err));
        } finally {
          setRetryRequested(false);
        }
        break;

      case 'clone':
        setShouldShowCloneModal(true);
        break;

      case 'delete':
        setShouldShowDeletionModal(true);
        setDeletionErrorMessage(null);
        break;

      default:
        console.error(`Unknown action '${action}'`);
        break;
    }
  }

  const handleCloneNameChanged = (e: any) => {
    setCloneName(e.target.value || '');
  }

  const handleCloneConfirmed = async () => {
    if (!workflow) {
      return;
    }

    setCloning(true);
    setCloneErrorMessage(null);

    try {
      const clonedWorkflow = await cloneWorkflow(workflow.uuid, {
        name: cloneName
      }, abortSignal);

      setWorkflow(clonedWorkflow);
      setShouldShowCloneModal(false);
      setCloning(false);
      setCloneErrorMessage(null);
      navigate('/workflows/' + encodeURIComponent(clonedWorkflow.uuid));
    } catch (err) {
        if (isCancel(err)) {
          console.log("Request canceled: " + err.message);
          return;
        }
        console.dir(err);
        setCloneErrorMessage('Failed to clone Workflow: ' +
          catchableToString(err));
    } finally {
      setCloning(false);
    }
  }

  const handleCloneCancelled = () => {
    setShouldShowCloneModal(false);
    setCloning(false);
    setCloneErrorMessage(null);
  };

  const handleDeletionConfirmed = async () => {
    if (!workflow) {
      return;
    }

    setDeleting(true);
    setDeletionErrorMessage(null);

    try {
      await deleteWorkflow(workflow.uuid);
      navigate('/workflows', { replace: true });
    } catch (err) {
      if (isCancel(err)) {
        console.log("Request canceled: " + err.message);
        return;
      }
      console.dir(err);
      setDeletionErrorMessage(`Failed to clone Workflow "${workflow.name}": ` +
        catchableToString(err));
    } finally {
      setDeleting(false);
    }
  }

  const handleDeletionCanceled = () => {
    setShouldShowDeletionModal(false);
    setDeleting(false);
    setDeletionErrorMessage(null);
  };

  useEffect(() => {
    if (uuid === 'new') {
      document.title = 'CloudReactor - Create Workflow';
    } else if (!workflow && !isWorkflowLoading && !loadErrorMessage) {
      document.title = `CloudReactor - Loading Workflow ...`
      loadWorkflowDetails();
    } else if (workflow) {
      updateTitle(workflow);
    } else {
      document.title = `CloudReactor - Workflow not found`
    }
  }, [workflow, isWorkflowLoading, loadErrorMessage]);

  useEffect(() => {
    return () => {
      if (selfInterval) {
        clearInterval(selfInterval);
      }
    };
  }, []);

  if (errorMessage) {
    return (
      <Alert variant="danger">
      { errorMessage }
      </Alert>
    );
  }

  if (!workflow) {
    return <Loading />
  }

  const lwe = workflow.latest_workflow_execution;

  return (
    <div className={styles.container}>
      <BreadcrumbBar
        rootUrl="/workflows" rootLabel="Workflows"
        firstLevel={workflow.name}
      />
      <div>
        <ButtonToolbar>
          {
            (accessLevel >= C.ACCESS_LEVEL_TASK) && (
              <ActionButton cbData={workflow} onActionRequested={handleActionRequested}
                action="start" faIconName="play" label="Start"
                disabled={!workflow.uuid}
                inProgress={isStarting} inProgressLabel="Starting ..." />
            )
          }

          {
            (accessLevel >= C.ACCESS_LEVEL_TASK) && (
              <ActionButton cbData={lwe} action="retry" faIconName="redo" label="Retry"
                onActionRequested={handleActionRequested}
                inProgress={isRetryRequested} inProgressLabel="Retrying ..."
                disabled={!lwe || (lwe.status === C.WORKFLOW_EXECUTION_STATUS_RUNNING)} />
            )
          }

          {
            (accessLevel >= C.ACCESS_LEVEL_DEVELOPER) && (
              <ActionButton
                faIconName="clone" label="Clone" action="clone"
                disabled={isCloning || isDeleting} inProgress={isCloning}
                onActionRequested={handleActionRequested} />
            )
          }

          <ConfirmationModal shouldShow={shouldShowCloneModal}
            disabled={isCloning || isDeleting} title="Clone Workflow"
            confirmLabel="Clone"
            onConfirm={handleCloneConfirmed}
            onCancel={handleCloneCancelled}>
            <div>
              {
                cloneErrorMessage &&
                <Alert variant="danger">
                  { cloneErrorMessage }
                  <p>
                    Please ensure the name of the cloned Workflow does not conflict
                    with an existing Workflow.
                  </p>
                </Alert>
              }

              <Form>
                <FormGroup>
                  <FormLabel>Name</FormLabel>
                  <FormControl name="name" value={cloneName || ''}
                    onChange={handleCloneNameChanged}/>
                </FormGroup>
              </Form>
            </div>
          </ConfirmationModal>

          {
            (accessLevel >= C.ACCESS_LEVEL_DEVELOPER) && (
              <ActionButton cbData={workflow} action="delete"
                onActionRequested={handleActionRequested}
                faIconName="trash" label="Delete"
                inProgress={isDeleting} inProgressLabel="Deleting"
                disabled={!workflow.uuid} />
            )
          }

          <ConfirmationModal shouldShow={shouldShowDeletionModal}
            disabled={!workflow.uuid || isDeleting} title="Delete Workflow"
            confirmLabel="Delete"
            onConfirm={handleDeletionConfirmed}
            onCancel={handleDeletionCanceled}
            confirmButtonVariant="danger">
            <div>
              {
                deletionErrorMessage &&
                <Alert variant="danger">
                  { deletionErrorMessage }
                </Alert>
              }

              <div>
                Are you sure you want to delete this Workflow?
                This will delete all Workflow Executions and Alerts associated with this Workflow.
              </div>
            </div>
          </ConfirmationModal>
        </ButtonToolbar>
      </div>
      {
        workflow &&
        <WorkflowEditor workflow={workflow}
          workflowExecution={workflowExecution}
          tab={selectedTab}
          onTabChanged={handleTabChange}
          onWorkflowChanged={handleWorkflowChanged}
          onActionError={handleActionError}
          onWorkflowExecutionUpdated={handleWorkflowExecutionUpdated} />
      }
    </div>
  );
}

export default abortableHoc(WorkflowDetail);
