import { AxiosError, isCancel } from 'axios';

import {
  RunEnvironment, WorkflowSummary
} from '../../../types/domain_types';


import {
  makeEmptyResultsPage,
  fetchRunEnvironments,
  deleteWorkflow,
  fetchWorkflowSummaries,
  fetchWorkflowsInErrorCount,
  startWorkflowExecution,
  stopWorkflowExecution,
  saveWorkflow
} from '../../../utils/api';

import React, {Fragment, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { Alert } from 'react-bootstrap';

import { BootstrapVariant } from '../../../types/ui_types';
import * as C from '../../../utils/constants';
import * as UIC from '../../../utils/ui_constants';
import { GlobalContext } from '../../../context/GlobalContext';

import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import FailureCountAlert from '../../../components/common/FailureCountAlert';
import ConfirmationModal from '../../../components/common/ConfirmationModal';

import { transformSearchParams, updateSearchParams } from '../../../utils/url_search';

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
  const [workflowsInErrorCount, setWorkflowsInErrorCount] = useState(0);
  const [loadWorkflowsAbortController, setLoadWorkflowsAbortController] = useState<AbortController | null>(null);
  const [loadWorkflowsInErrorAbortController, setLoadWorkflowsInErrorAbortController] = useState<AbortController | null>(null);
  const [shouldShowDeletionModal, setShouldShowDeletionModal] = useState(false);
  const [workflow, setWorkflow] = useState<WorkflowSummary | null>(null);
  const [selfTimeout, setSelfTimeout] = useState<NodeJS.Timeout | null>(null);
  const [flashBody, setFlashBody] = useState<string | null>(null);
  const [flashAlertVariant, setFlashAlertVariant] = useState<BootstrapVariant>('info');
  const [isDeleting, setDeleting] = useState(false);

  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const mounted = useRef(false);

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

  const loadWorkflowsInErrorCount = async () => {
    const {
      q,
      selectedRunEnvironmentUuids,
      selectedStatuses
    } = transformSearchParams(searchParams);

    if (loadWorkflowsInErrorAbortController) {
      loadWorkflowsInErrorAbortController.abort('Operation superceded');
    }
    const updatedLoadWorkflowsInErrorAbortController = new AbortController();
    setLoadWorkflowsInErrorAbortController(updatedLoadWorkflowsInErrorAbortController);

    try {
      setWorkflowsInErrorCount(await fetchWorkflowsInErrorCount({
        groupId: currentGroup?.id,
        q,
        runEnvironmentUuids: selectedRunEnvironmentUuids,
        statuses: selectedStatuses,
        abortSignal
      }));

      setLoadWorkflowsInErrorAbortController(null);
    } catch (error) {
      if (!isCancel(error)) {
        //console.('Request canceled: ' + error.message);
        return;
      }
    }
  };

  const loadWorkflows = async () => {
    // This would cause the search input to lose focus, because it would be
    // temporarily replaced with a loading indicator.
    //setAreWorkflowsLoading(true);

    if (loadWorkflowsAbortController) {
      loadWorkflowsAbortController.abort('Operation superceded');
    }

    if (!mounted.current) {
      return;
    }

    const updatedLoadWorkflowsAbortController = new AbortController();
    setLoadWorkflowsAbortController(updatedLoadWorkflowsAbortController);

    if (selfTimeout) {
      clearTimeout(selfTimeout);
      setSelfTimeout(null);
    }

    const {
      q,
      sortBy,
      descending,
      selectedRunEnvironmentUuids,
      selectedStatuses,
      rowsPerPage,
      currentPage,
    } = transformSearchParams(searchParams, true);

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
        statuses: selectedStatuses,
        abortSignal
      });

      if (mounted.current) {
        setLoadWorkflowsAbortController(null);
        setWorkflowPage(workflowPage);
        setAreWorkflowsLoading(false);

        await loadWorkflowsInErrorCount();

        if (mounted.current) {
          setSelfTimeout(setTimeout(loadWorkflows, UIC.TASK_REFRESH_INTERVAL_MILLIS));
        }
      }
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request canceled: ' + error.message);
        return;
      }

      if (selfTimeout) {
        clearInterval(selfTimeout);
        setSelfTimeout(null);
      }

      setLastLoadErrorMessage('Failed to load Workflows');
    } finally {
      setAreWorkflowsLoading(false);
    }
  };

  const handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    updateSearchParams(searchParams, setSearchParams, rowsPerPage, 'rows_per_page');
  };

  const handleSortChanged = useCallback(async (ordering?: string, toggleDirection?: boolean) => {
    updateSearchParams(searchParams, setSearchParams, ordering, 'sort_by');
  }, [location]);

  const handleQueryChanged = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const q = event.target.value;
    updateSearchParams(searchParams, setSearchParams, q, 'q');
  };

  const handlePageChanged = useCallback((currentPage: number) => {
    updateSearchParams(searchParams, setSearchParams, currentPage + 1, 'page');
  }, [location]);

  const handleSelectedRunEnvironmentUuidsChanged = (
    selectedRunEnvironmentUuids?: string[]
  ) => {
    updateSearchParams(searchParams, setSearchParams, selectedRunEnvironmentUuids,
      'run_environment__uuid');
  };

  const handleSelectedStatusesChanged = (
    statuses?: string[]
  ) => {
    updateSearchParams(searchParams, setSearchParams, statuses, 'latest_workflow_execution__status');
  };



  /*
  handlePrev = (): void =>
    this.setState({
      currentPage: this.state.currentPage - 1
    }, this.loadWorkflows);

  handleNext = (): void =>
    this.setState({
      currentPage: this.state.currentPage + 1
    }, this.loadWorkflows); */

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
  }, [workflow]);

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
  }, []);

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
  }, []);

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
  }, []);

  const handleCreateWorkflow = useCallback((action: string | undefined, cbData: any) => {
    navigate('/workflows/new')
  }, []);

  const cleanupLoading = () => {
    if (loadWorkflowsAbortController) {
      loadWorkflowsAbortController.abort('Operation canceled after component unmounted');
    }

    if (loadWorkflowsInErrorAbortController) {
      loadWorkflowsInErrorAbortController.abort('Operation canceled after component unmounted');
    }

    if (selfTimeout) {
      clearTimeout(selfTimeout);
    }
  };

  useEffect(() => {
    mounted.current = true;

    loadRunEnvironments()

    return () => {
      mounted.current = false;
      cleanupLoading();
    };
  }, []);

  useEffect(() => {
    loadWorkflows();

    return () => {
      cleanupLoading();
    };
  }, [location]);

  const {
    q,
    sortBy,
    descending,
    selectedRunEnvironmentUuids,
    selectedStatuses,
    rowsPerPage,
    currentPage
  } = transformSearchParams(searchParams, true);

  const finalSortBy = (sortBy ?? 'name');
  const finalDescending = descending ?? false;

  const workflowTableProps = {
    handleSelectedRunEnvironmentUuidsChanged,
    handleSelectedStatusesChanged,
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
    selectedRunEnvironmentUuids,
    selectedStatuses,
  };

  return (
    <Fragment>
      {
        (areRunEnvironmentsLoading || areWorkflowsLoading) ? (
          <Loading />
        ) : (
          <div className={styles.container}>
            <FailureCountAlert itemName="Workflow" count={workflowsInErrorCount} />

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

            {
              lastLoadErrorMessage &&
              <Alert variant="warning">
                { lastLoadErrorMessage }
              </Alert>
            }

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
