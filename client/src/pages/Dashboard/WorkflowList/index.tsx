import { AxiosError, isCancel } from 'axios';

import {
  RunEnvironment, WorkflowSummary
} from '../../../types/domain_types';


import {
  makeEmptyResultsPage,
  fetchRunEnvironments,
  deleteWorkflow,
  fetchWorkflowSummaries,
  startWorkflowExecution,
  stopWorkflowExecution,
  saveWorkflow
} from '../../../utils/api';

import React, {Fragment, useCallback, useContext, useEffect, useState } from 'react';
import { useHistory } from 'react-router-dom';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { Alert } from 'react-bootstrap';

import { BootstrapVariant } from '../../../types/ui_types';
import * as C from '../../../utils/constants';
import * as UIC from '../../../utils/ui_constants';
import { GlobalContext } from '../../../context/GlobalContext';

import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import FailureCountAlert from '../../../components/common/FailureCountAlert';
import ConfirmationModal from '../../../components/common/ConfirmationModal';

import { getParams, setURL } from '../../../utils/url_search';

import ActionButton from '../../../components/common/ActionButton';
import Loading from '../../../components/Loading';
import WorkflowTable from '../../../components/WorkflowList/WorkflowTable';
import styles from './index.module.scss';
import '../../../components/Tasks/style.scss';

const WorkflowList = (props: AbortSignalProps) => {
  const {
    abortSignal
  } = props;

  const { currentGroup } = useContext(GlobalContext);


  const [areRunEnvironmentsLoading, setAreRunEnvironmentsLoading] = useState(false);
  const [lastLoadErrorMessage, setLastLoadErrorMessage] = useState<string | null>(null);
  const [runEnvironments, setRunEnvironments] = useState<Array<RunEnvironment>>([]);
  const [areWorkflowsLoading, setAreWorkflowsLoading] = useState(true);
  const [workflowPage, setWorkflowPage] = useState(
    makeEmptyResultsPage<WorkflowSummary>());
  const [shouldShowDeletionModal, setShouldShowDeletionModal] = useState(false);
  const [workflow, setWorkflow] = useState<WorkflowSummary | null>(null);
  const [selfInterval, setSelfInterval] = useState<any>(null);
  const [flashBody, setFlashBody] = useState<string | null>(null);
  const [flashAlertVariant, setFlashAlertVariant] = useState<BootstrapVariant>('info');
  const [isDeleting, setDeleting] = useState(false);

  const history = useHistory();

  const loadRunEnvironments = useCallback(async () => {
    setAreRunEnvironmentsLoading(true);
    try {
      const page = await fetchRunEnvironments({
        groupId: currentGroup?.id,
        abortSignal
      });

      setRunEnvironments(page.results);
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request canceled: ' + error.message);
      }
    } finally {
      setAreRunEnvironmentsLoading(false);
    }
  }, []);

  const loadWorkflows = useCallback(async () => {
    // This would cause the search input to lose focus, because it would be
    // temporarily replaced with a loading indicator.
    //setAreWorkflowsLoading(true);
    const {
      q,
      sortBy,
      descending,
      selectedRunEnvironmentUuids,
      rowsPerPage,
      currentPage,
    } = getParams(history.location.search);

    const offset = currentPage * rowsPerPage;

    try {
      const workflowPage = await fetchWorkflowSummaries({
        groupId: currentGroup?.id,
        sortBy,
        descending,
        offset,
        maxResults: rowsPerPage,
        q,
        runEnvironmentUuids: selectedRunEnvironmentUuids,
        abortSignal
      });

      setWorkflowPage(workflowPage);
      setAreWorkflowsLoading(false);
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request canceled: ' + error.message);
        return;
      }

      if (selfInterval) {
        clearInterval(selfInterval);
        setSelfInterval(null);
      }

      setLastLoadErrorMessage('Failed to load Workflows');
    } finally {
      setAreWorkflowsLoading(false);
    }

    return;
  }, [history.location]);

  const handleSelectItemsPerPage = useCallback((
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    setURL(history.location, history, rowsPerPage, 'rows_per_page');
    loadWorkflows();
  }, [history.location, loadWorkflows]);

  const handleSortChanged = useCallback(async (ordering?: string, toggleDirection?: boolean) => {
    setURL(history.location, history, ordering, 'sort_by');
    loadWorkflows();
  }, [history.location, loadWorkflows]);

  const handleQueryChanged = useCallback((
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const q = event.target.value;
    setURL(history.location, history, q, 'q');
    loadWorkflows();
  }, [history.location, loadWorkflows]);

  const handleRunEnvironmentChanged = useCallback((
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const selectedRunEnvironmentUuid = event.target.value;
    setURL(history.location, history, selectedRunEnvironmentUuid, 'selected_run_environment_uuid');
    loadWorkflows();
  }, [history.location, loadWorkflows]);

  const handlePageChanged = useCallback((currentPage: number) => {
    setURL(history.location, history, currentPage + 1, 'page');
    loadWorkflows();
  }, [history.location, loadWorkflows]);

  const handleSelectedRunEnvironmentUuidsChanged = useCallback((
    selectedRunEnvironmentUuids?: string[]
  ) => {
    setURL(history.location, history, selectedRunEnvironmentUuids,
      'selected_run_environment_uuid');
    loadWorkflows();
  }, [history.location, loadWorkflows]);

  /*
  handlePrev = (): void =>
    this.setState({
      currentPage: this.state.currentPage - 1
    }, this.loadWorkflows);

  handleNext = (): void =>
    this.setState({
      currentPage: this.state.currentPage + 1
    }, this.loadWorkflows); */

  const failedWorkflowCount = useCallback((workflows: WorkflowSummary[]): number => {
    let count = 0;
    workflows.forEach(wf => {
      if (wf.enabled && wf.latest_workflow_execution &&
          ((wf.latest_workflow_execution.status === C.WORKFLOW_EXECUTION_STATUS_FAILED) ||
           (wf.latest_workflow_execution.status === C.WORKFLOW_EXECUTION_STATUS_TERMINATED_AFTER_TIME_OUT))) {
        count += 1;
      }
    });

    return count;
  }, []);

  const handleDeletionRequest = useCallback((wf: WorkflowSummary) => {
    setShouldShowDeletionModal(true);
    setWorkflow(wf);
  }, []);

  const handleDeletionConfirmed = useCallback(async () => {
    if (!workflow) {
      console.error('No Workflow to delete');
      return;
    }

    setFlashBody(null);
    setDeleting(true);

    try {
      await deleteWorkflow(workflow.uuid);

      setFlashAlertVariant('success');
      setFlashBody(`Successfully deleted Workflow "${workflow.name}."`);
      setDeleting(false);
      await loadWorkflows();
    } catch (e) {
      setFlashAlertVariant('danger');
      setFlashBody(`Failed to delete Workflow "${workflow.name}."`);
      setDeleting(false);
    } finally {
      setShouldShowDeletionModal(false);
      setWorkflow(null);
    }
  }, [workflow, loadWorkflows]);

  const handleDeletionCancelled = useCallback(() => {
    setWorkflow(null);
    setShouldShowDeletionModal(false);
    setDeleting(false);
  }, [setWorkflow, setShouldShowDeletionModal]);

  const handleEditRequest = useCallback(async (wf: WorkflowSummary, data: any) => {
    try {
      const updatedWorkflow = Object.assign({}, wf, data);
      await saveWorkflow(updatedWorkflow);
      loadWorkflows();
    } catch (err) {
      let updatedFlashBody = "Failed to update Workflow";

      if ((err instanceof AxiosError) && err.response && err.response.data) {
        updatedFlashBody += ': ' + JSON.stringify(err.response.data);
      }

      setFlashAlertVariant('danger');
      setFlashBody(updatedFlashBody);
    }
  }, [loadWorkflows]);

  const handleStartRequest = useCallback(async (wf: WorkflowSummary) => {
    if (!wf) {
      console.error('No Workflow to start');
      return;
    }

    setFlashBody(null);
    setWorkflow(wf);

    try {
      await startWorkflowExecution(wf.uuid);
      setFlashAlertVariant('success');
      setFlashBody(`Successfully started Workflow "${wf.name}".`);
      await loadWorkflows();
    } catch (e) {
      setFlashAlertVariant('danger');
      setFlashBody(`Failed to start Workflow "${wf.name}".`);
    } finally {
      setWorkflow(null);
    }
  }, [loadWorkflows]);

  const handleStopRequest = useCallback(async (wf: WorkflowSummary) => {
    if (!wf || !wf.latest_workflow_execution) {
      console.error('No Workflow execution to stop');
      return;
    }
    setFlashBody(null);
    setWorkflow(wf);

    try {
      await stopWorkflowExecution(wf.latest_workflow_execution.uuid);

      setFlashAlertVariant('success');
      setFlashBody(`Successfully stopped Workflow "${wf.name}".`);
      await loadWorkflows();
    } catch (e) {
      setFlashAlertVariant('danger');
      setFlashBody(`Failed to stop Workflow "${wf.name}".`);
    } finally {
      setWorkflow(null);
    }
  }, [loadWorkflows]);

  const handleCreateWorkflow = useCallback((action: string | undefined, cbData: any) => {
    history.push('/workflows/new')
  }, []);

  useEffect(() => {
    loadRunEnvironments()
  }, []);

  useEffect(() => {
    loadWorkflows().then(_dummy => {
      const interval = setInterval(loadWorkflows,
        UIC.TASK_REFRESH_INTERVAL_MILLIS);
      setSelfInterval(interval);
    });

    return () => {
      if (selfInterval) {
        clearInterval(selfInterval);
      }
    };
  }, []);

  const {
    q,
    sortBy,
    descending,
    selectedRunEnvironmentUuids,
    rowsPerPage,
    currentPage
  } = getParams(history.location.search);

  const finalSortBy = (sortBy ?? 'name');
  const finalDescending = descending ?? false;

  const workflowTableProps = {
    handleSelectedRunEnvironmentUuidsChanged,
    handleQueryChanged,
    loadWorkflows,
    handleSortChanged,
    handlePageChanged,
    handleSelectItemsPerPage,
    handleStartRequest,
    handleStopRequest,
    handleEditRequest,
    handleDeletionRequest,
    q,
    sortBy: finalSortBy,
    descending : finalDescending,
    currentPage,
    rowsPerPage,
    workflowPage,
    workflow,
    runEnvironments,
    selectedRunEnvironmentUuids
  };

  return (
    <Fragment>
      {
        (areRunEnvironmentsLoading || areWorkflowsLoading) ? (
          <Loading />
        ) : (
          <div className={styles.container}>
            <FailureCountAlert count={failedWorkflowCount(workflowPage.results)}
             itemName="Workflow" />
            {
              flashBody &&
              <Alert variant={flashAlertVariant || 'success'}>
                {flashBody}
              </Alert>
            }

            <BreadcrumbBar
              firstLevel="Workflows"
              secondLevel={null}
            />

            <div>
              <ActionButton action="create" label="Create Workflow ..."
                faIconName="plus-square"
                onActionRequested={handleCreateWorkflow} />
            </div>

            <WorkflowTable {... workflowTableProps} />

            {workflow && <ConfirmationModal shouldShow={shouldShowDeletionModal}
            disabled={isDeleting} title="Delete Workflow"
            body={`Delete Workflow "${workflow.name}"?`}
            confirmLabel="Delete" cancelLabel="Cancel"
            confirmButtonVariant="danger"
            onConfirm={handleDeletionConfirmed}
            onCancel={handleDeletionCancelled} /> }
          </div>
        )
      }
    </Fragment>
  );
}

export default abortableHoc(WorkflowList);
