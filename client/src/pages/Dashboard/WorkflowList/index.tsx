import _ from 'lodash';

import { isCancel } from 'axios';

import {
  RunEnvironment, WorkflowSummary
} from '../../../types/domain_types';

import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import {
  ResultsPage,
  makeEmptyResultsPage,
  fetchRunEnvironments,
  deleteWorkflow,
  fetchWorkflowSummaries,
  startWorkflowExecution,
  stopWorkflowExecution,
  saveWorkflow
} from '../../../utils/api';

import React, { Component, Fragment } from 'react';
import { RouteComponentProps, withRouter } from 'react-router';

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

interface Props extends RouteComponentProps<any> {
}

interface State {
  flashBody?: any;
  flashAlertVariant?: BootstrapVariant;
  isLoading: boolean;
  workflowPage: ResultsPage<WorkflowSummary>;
  currentPage: number;
  rowsPerPage: number;
  modalWindow: boolean;
  workflow: WorkflowSummary | null;
  shouldShowDeletionModal: boolean;
  isDeleting: boolean;
  interval: any;
  areRunEnvironmentsLoading: boolean;
  runEnvironments: RunEnvironment[];
}


type InnerProps = Props & AbortSignalProps;

class WorkflowList extends Component<InnerProps, State> {
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      areRunEnvironmentsLoading: true,
      runEnvironments: [],
      workflowPage: { count: 0, results: [] },
      isLoading: true,
      currentPage: 0,
      rowsPerPage: UIC.DEFAULT_PAGE_SIZE,
      modalWindow: false,
      workflow: null,
      shouldShowDeletionModal: false,
      isDeleting: false,
      interval: null,
    };

    this.loadWorkflows = _.debounce(this.loadWorkflows, 250) as () => Promise<void>;
  }

  async componentDidMount() {
    await this.loadWorkflows();
    await this.loadRunEnvironments();
    const interval = setInterval(this.loadWorkflows,
      UIC.TASK_REFRESH_INTERVAL_MILLIS);
    this.setState({
      interval
    });
  }

  componentWillUnmount() {
    if (this.state.interval) {
      clearInterval(this.state.interval);
    }
  }

  async loadRunEnvironments() {
    const {
      abortSignal
    } = this.props;

    const { currentGroup } = this.context;

    try {
      const page = await fetchRunEnvironments({
        groupId: currentGroup?.id,
        abortSignal
      });
      this.setState({
        runEnvironments: page.results,
        areRunEnvironmentsLoading: false,
      });
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request cancelled: ' + error.message);
        return;
      }
    }
  }

  loadWorkflows = async (): Promise<void> => {
    // get query params (if any) from url -- to load workflows with
    const {
      q,
      sortBy,
      descending,
      selectedRunEnvironmentUuid,
      rowsPerPage = UIC.DEFAULT_PAGE_SIZE,
      currentPage = 0,
    } = getParams(this.props.location.search);

    const offset = currentPage * rowsPerPage;

    const { currentGroup } = this.context;

    let workflowPage: ResultsPage<WorkflowSummary> =
      makeEmptyResultsPage();

    try {
      workflowPage = await fetchWorkflowSummaries({
        groupId: currentGroup?.id,
        runEnvironmentUuid: selectedRunEnvironmentUuid,
        q,
        sortBy,
        descending,
        offset,
        maxResults: rowsPerPage,
        abortSignal: this.props.abortSignal
      });
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request cancelled: ' + error.message);
        return;
      }
    }

    this.setState({
      workflowPage,
      isLoading: false,
    });
  }

  handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ): void => {
    const value = event.target.value;
    this.setState({
      rowsPerPage: parseInt(value)
    }, this.loadWorkflows);
  };

  handleSortChanged = async (ordering?: string, toggleDirection?: boolean) => {
    setURL(this.props.location, this.props.history, ordering, 'sort_by')
    this.loadWorkflows();
  };

  handleQueryChanged = (
    event: React.ChangeEvent<HTMLInputElement>
  ): void => {
    setURL(this.props.location, this.props.history, event.target.value, 'q');
    this.loadWorkflows();
  };

  handleRunEnvironmentChanged = (
    event: React.ChangeEvent<HTMLInputElement>
  ): void => {
    setURL(this.props.location, this.props.history, event.target.value, 'selected_run_environment_uuid');
    this.loadWorkflows();
  };

  handlePageChanged = (currentPage: number): void => {
    this.setState({ currentPage }, this.loadWorkflows);
  }

  handlePrev = (): void =>
    this.setState({
      currentPage: this.state.currentPage - 1
    }, this.loadWorkflows);

  handleNext = (): void =>
    this.setState({
      currentPage: this.state.currentPage + 1
    }, this.loadWorkflows);

  getWorkflow = async (id: number): Promise<void> => {
    const workflow = this.state.workflowPage.results.find(workflow => workflow.uuid === '' + id);

    if (workflow) {
      this.setState({
        modalWindow: true,
        workflow
      });
    }
  };

  failedWorkflowCount = (workflows: WorkflowSummary[]): number => {
    let count = 0;
    workflows.forEach(workflow => {
      if (workflow.enabled && workflow.latest_workflow_execution &&
          ((workflow.latest_workflow_execution.status === C.WORKFLOW_EXECUTION_STATUS_FAILED) ||
           (workflow.latest_workflow_execution.status === C.WORKFLOW_EXECUTION_STATUS_TERMINATED_AFTER_TIME_OUT))) {
        count += 1;
      }
    });

    return count;
  };

  private handleDeletionRequest = (workflow: WorkflowSummary) => {
    this.setState({
      shouldShowDeletionModal: true,
      workflow
    });
  };

  private handleDeletionConfirmed = async () => {
    this.setState({
      flashBody: null,
      isDeleting: true
    });

    const {
      workflow
    } = this.state;

    if (!workflow) {
      console.error('No Workflow to delete');
      return;
    }

    try {
      await deleteWorkflow(workflow.uuid);

      this.setState({
        flashAlertVariant: 'success',
        flashBody: `Successfully deleted Workflow "${workflow.name}."`,
        shouldShowDeletionModal: false,
        isDeleting: false,
        workflow: null
      }, () => this.loadWorkflows());
    } catch (e) {
      this.setState({
        flashAlertVariant: 'danger',
        flashBody: `Failed to delete Workflow "${workflow.name}."`,
        shouldShowDeletionModal: false,
        isDeleting: false,
        workflow: null
      });
    }
  }

  handleDeletionCancelled = () => {
    this.setState({
      workflow: null,
      shouldShowDeletionModal: false,
      isDeleting: false
    });
  }

  private handleEditRequest = async (workflow: WorkflowSummary, data: any) => {

    try {
      const updatedWorkflow = Object.assign({}, workflow, data);
      await saveWorkflow(updatedWorkflow);
      this.loadWorkflows();
    } catch (err) {
      let flashBody = "Failed to update workflow";

      if (err.response && err.response.data) {
        flashBody += ': ' + JSON.stringify(err.response.data);
      }

      this.setState({
        flashAlertVariant: 'danger',
        flashBody
      })
    }
  };

  private handleStartRequest = async (workflow: WorkflowSummary) => {
    if (!workflow) {
      console.error('No Workflow to start');
      return;
    }

    this.setState({
      flashBody: null,
      workflow
    });

    try {
      await startWorkflowExecution(workflow.uuid);

      this.setState({
        flashAlertVariant: 'success',
        flashBody: `Successfully started Workflow "${workflow.name}".`,
        workflow: null
      }, () => this.loadWorkflows());
    } catch (e) {
      this.setState({
        flashAlertVariant: 'danger',
        flashBody: `Failed to start Workflow "${workflow.name}".`,
        workflow: null
      });
    }
  };

  private handleStopRequest = async (workflow: WorkflowSummary) => {
    if (!workflow || !workflow.latest_workflow_execution) {
      console.error('No Workflow execution to stop');
      return;
    }

    this.setState({
      flashBody: null,
      workflow
    });

    try {
      await stopWorkflowExecution(workflow.latest_workflow_execution.uuid);

      this.setState({
        flashAlertVariant: 'success',
        flashBody: `Successfully stopped workflow "${workflow.name}".`,
        workflow: null
      }, () => this.loadWorkflows());
    } catch (e) {
      this.setState({
        flashAlertVariant: 'danger',
        flashBody: `Failed to stop workflow "${workflow.name}".`,
        workflow: null
      });
    }
  };

  renderWorkflowList() {
    const {
      workflow,
      workflowPage,
      shouldShowDeletionModal,
      isDeleting,
      flashBody,
      flashAlertVariant,
    } = this.state;

    const {
      q = '',
      sortBy = '',
      descending = false,
      selectedRunEnvironmentUuid = '',
      rowsPerPage = UIC.DEFAULT_PAGE_SIZE,
      currentPage = 0,
    } = getParams(this.props.location.search);

    const failedCount = this.failedWorkflowCount(workflowPage.results);

    return (
      <div className={styles.container}>
        <FailureCountAlert count={failedCount} itemName="Workflow" />
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
            onActionRequested={this.handleCreateWorkflow} />
        </div>

        <WorkflowTable
          selectedRunEnvironmentUuid={selectedRunEnvironmentUuid}
          q={q}
          sortBy={sortBy}
          descending={descending}
          handleSortChanged={this.handleSortChanged}
          handleQueryChanged={this.handleQueryChanged}
          loadWorkflows={this.loadWorkflows}
          handleRunEnvironmentChanged={this.handleRunEnvironmentChanged}
          handlePageChanged={this.handlePageChanged}
          handleSelectItemsPerPage={this.handleSelectItemsPerPage}
          handleEditRequest={this.handleEditRequest}
          handleDeletionRequest={this.handleDeletionRequest}
          handleStartRequest={this.handleStartRequest}
          handleStopRequest={this.handleStopRequest}
          {... this.state}
        />

        {workflow && <ConfirmationModal shouldShow={shouldShowDeletionModal}
         disabled={isDeleting} title="Delete Workflow"
         body={`Delete Workflow "${workflow.name}"?`}
         confirmLabel="Delete" cancelLabel="Cancel"
         confirmButtonVariant="danger"
         onConfirm={this.handleDeletionConfirmed}
         onCancel={this.handleDeletionCancelled} /> }
      </div>

    );
  }

  public render() {
    return (
      <Fragment>
        {
          this.state.isLoading
          ? <Loading />
          : this.renderWorkflowList()
        }
      </Fragment>
    );

  }

  handleCreateWorkflow = (action: string | undefined, cbData: any) => {
    this.props.history.push('/workflows/new')
  };
}

export default withRouter(abortableHoc(WorkflowList));
