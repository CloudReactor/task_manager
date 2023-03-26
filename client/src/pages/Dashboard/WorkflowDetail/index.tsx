import {makeNewWorkflow, Workflow, WorkflowExecution} from '../../../types/domain_types';
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

import React, { Component, Fragment } from 'react';
import { withRouter, RouteComponentProps } from 'react-router';

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

import Charts from './Charts';
import ActionButton from '../../../components/common/ActionButton';
import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import ConfirmationModal from '../../../components/common/ConfirmationModal';
import Loading from '../../../components/Loading';
import WorkflowEditor from '../../../components/WorkflowDetails/WorkflowEditor';
import WorkflowExecutionsTable from '../../../components/WorkflowDetails/WorkflowExecutionsTable';
import styles from './index.module.scss';

type PathParamsType = {
  uuid: string;
};

type Props = RouteComponentProps<PathParamsType>;

interface State {
  workflow?: Workflow;
  workflowExecution?: WorkflowExecution;
  isStarting: boolean;
  isRetryRequested: boolean;
  errorMessage?: string;
  shouldShowCloneModal: boolean;
  isCloning: boolean;
  cloneName?: string;
  cloneErrorMessage?: string;
  shouldShowDeletionModal: boolean;
  isDeleting: boolean;
  deletionErrorMessage?: string;
  interval: any;
  selectedTab: string | null;
}

class WorkflowDetail extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    const workflow = (this.props.match.params.uuid === 'new') ?
      makeNewWorkflow() : undefined;

    this.state = {
      workflow,
      isStarting: false,
      isRetryRequested: false,
      shouldShowCloneModal: false,
      isCloning: false,
      shouldShowDeletionModal: false,
      isDeleting: false,
      interval: null,
      selectedTab: 'graph'
    };
  }

  async componentDidMount() {
    document.title = 'CloudReactor - Workflow Details';
    if (this.props.match.params.uuid !== 'new') {
      await this.loadWorkflowDetails();
    }
  }

  componentWillUnmount() {
    if (this.state.interval) {
      clearInterval(this.state.interval);
    }
  }

  onTabChange = (selectedTab: string | null) => {
    const value = selectedTab?.toLowerCase() ?? null;
    this.setState({
      selectedTab: value
    });
  }

  async loadWorkflowDetails() {
    let workflow: Workflow | null = null;
    try {
      const uuid = this.props.match.params.uuid;
      workflow = await fetchWorkflow(uuid);

      this.updateTitle(workflow);

      this.setState({
        workflow,
        errorMessage: undefined
      });
    } catch (error) {
      let errorMessage = 'An error occurred loading this Workflow.'

      if (error.isAxiosError) {
        if (error.response.status === 404) {
          errorMessage = "Can't find this Workflow. Perhaps it was removed?"
        }
      }

      this.setState({
        errorMessage
      });
    }

    await this.loadLatestWorkflowExecution();
  }

  loadLatestWorkflowExecution = async () => {
    const {
      workflow
    }  = this.state;

    let workflowExecution: WorkflowExecution | undefined;

    if (workflow && workflow.latest_workflow_execution) {
      workflowExecution = await fetchWorkflowExecution(
        workflow.latest_workflow_execution.uuid);
    }

    this.handleLatestWorkflowExecutionUpdated(workflowExecution);

    return workflowExecution;
  }

  handleWorkflowExecutionUpdated = (workflowExecution: WorkflowExecution) => {
    const {
      workflow
    }  = this.state;

    if (!workflow) {
      return;
    }

    const latestWorkflowExecution = workflow.latest_workflow_execution;

    if (latestWorkflowExecution && (latestWorkflowExecution.uuid === workflowExecution.uuid)) {
      this.handleLatestWorkflowExecutionUpdated(workflowExecution);
    }
  }

  handleLatestWorkflowExecutionUpdated = (workflowExecution: WorkflowExecution | undefined) => {
    let {
      interval
    } = this.state;

    if (workflowExecution && shouldRefreshWorkflowExecution(workflowExecution)) {
      if (!interval) {
        interval = setInterval(this.loadLatestWorkflowExecution,
            UIC.TASK_REFRESH_INTERVAL_MILLIS);
      }
    } else {
      if (interval) {
        clearInterval(interval);
        interval = null;
      }
    }

    this.setState({
      workflowExecution,
      interval
    });
  }

  public render() {
    const accessLevel = accessLevelForCurrentGroup(this.context);

    if (!accessLevel) {
      return null;
    }

    const {
      workflow,
      workflowExecution,
      errorMessage,
      isStarting,
      isRetryRequested,
      shouldShowCloneModal,
      isCloning,
      cloneName,
      cloneErrorMessage,
      shouldShowDeletionModal,
      isDeleting,
      deletionErrorMessage,
      selectedTab
    } = this.state;

    console.log('WorkflowDetail.index rendering Workflow')
    console.dir(workflow);

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
                <ActionButton cbData={workflow} onActionRequested={this.handleActionRequested}
                  action="start" faIconName="play" label="Start"
                  disabled={!workflow.uuid}
                  inProgress={isStarting} inProgressLabel="Starting ..." />
              )
            }

            {
              (accessLevel >= C.ACCESS_LEVEL_TASK) && (
                <ActionButton cbData={lwe} action="retry" faIconName="redo" label="Retry"
                  onActionRequested={this.handleActionRequested}
                  inProgress={isRetryRequested} inProgressLabel="Retrying ..."
                  disabled={!lwe || (lwe.status === C.WORKFLOW_EXECUTION_STATUS_RUNNING)} />
              )
            }

            {
              (accessLevel >= C.ACCESS_LEVEL_DEVELOPER) && (
                <ActionButton
                  faIconName="clone" label="Clone" action="clone"
                  disabled={isCloning || isDeleting} inProgress={isCloning}
                  onActionRequested={this.handleActionRequested} />
              )
            }

            <ConfirmationModal shouldShow={shouldShowCloneModal}
              disabled={isCloning || isDeleting} title="Clone Workflow"
              confirmLabel="Clone"
              onConfirm={this.handleCloneConfirmed}
              onCancel={this.handleCloneCancelled}>
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
                      onChange={this.handleCloneNameChanged}/>
                  </FormGroup>
                </Form>
              </div>
            </ConfirmationModal>

            {
              (accessLevel >= C.ACCESS_LEVEL_DEVELOPER) && (
                <ActionButton cbData={workflow} action="delete"
                  onActionRequested={this.handleActionRequested}
                  faIconName="trash" label="Delete"
                  inProgress={isDeleting} inProgressLabel="Deleting"
                  disabled={!workflow.uuid} />
              )
            }

            <ConfirmationModal shouldShow={shouldShowDeletionModal}
              disabled={!workflow.uuid || isDeleting} title="Delete Workflow"
              confirmLabel="Delete"
              onConfirm={this.handleDeletionConfirmed}
              onCancel={this.handleDeletionCancelled}
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
                  This will delete all Workflow Executions and alerts associated with this Workflow.
                </div>
              </div>
            </ConfirmationModal>
          </ButtonToolbar>
        </div>
        {
          workflow &&
          <WorkflowEditor workflow={workflow}
           workflowExecution={workflowExecution}
           onTabChanged={this.onTabChange}
           onWorkflowChanged={this.handleWorkflowChanged} />
        }
        {
          (selectedTab !== 'graph')
          ? null
          : (workflow && workflow.latest_workflow_execution)
            ? this.renderExecutionsSection(workflow)
            : this.renderNoExecutionsSection()
        }
      </div>
    );
  }

  renderExecutionsSection(workflow: Workflow) {
    return (
      <Fragment>
        <Charts uuid={this.props.match.params.uuid} history={this.props.history} />
        <section>
          <hr/>
          <h2>Executions</h2>
          <WorkflowExecutionsTable
            workflow={workflow}
            onActionError={this.handleActionError}
            onWorkflowExecutionUpdated={this.handleWorkflowExecutionUpdated} />
        </section>
      </Fragment>
    );
  }

  renderNoExecutionsSection() {
    return (
      <h2 className="mt-5">
        This Workflow has not run yet. When it does, you&apos;ll be able to see
        a table of Workflow Executions here.
      </h2>
    );
  }

  handleWorkflowChanged = (workflow: Workflow) => {
    const oldWorkflow = this.state.workflow;

    this.setState({
      workflow
    });

    this.updateTitle(workflow);

    if (!oldWorkflow?.uuid && workflow.uuid) {
      this.props.history.replace('/workflows/' + encodeURIComponent(workflow.uuid));
    }
  }

  updateTitle = (workflow: Workflow) => {
    document.title = `CloudReactor - Workflow ${workflow.name}`;
  }

  handleActionRequested = async (action: string | undefined, cbData: any): Promise<void> => {
    switch (action) {
      case 'start':
        this.setState({
          isStarting: true
        });
        try {
          const workflowExecution = await startWorkflowExecution(cbData.uuid);
          this.props.history.push('/workflow_executions/' +
              encodeURIComponent(workflowExecution.uuid));
        } catch (e) {
          console.dir(e);
          this.setState({
            isStarting: false,
            errorMessage: e.message || 'Failed to start Workflow'
          });
        }
        break;

      case 'retry':
        this.setState({
          isRetryRequested: true
        });
        try {
          const workflowExecution = await retryWorkflowExecution(cbData.uuid);
          this.props.history.push('/workflow_executions/' +
              encodeURIComponent(workflowExecution.uuid));
        } catch (e) {
          console.dir(e);
          this.setState({
            isRetryRequested: false,
            errorMessage: e.message || 'Failed to retry Workflow Execution'
          });
        }
        break;

      case 'clone':
        this.setState({
          shouldShowCloneModal: true
        });
        break;

      case 'delete':
        this.setState({
          shouldShowDeletionModal: true,
          deletionErrorMessage: undefined
        });
        break;

      default:
        console.error(`Unknown action '${action}'`);
        break;
    }
  }

  handleActionError = (action: string, cbData: any, errorMessage: string) => {
    this.setState({
      errorMessage
    });
  }

  handleCloneNameChanged = (e: any) => {
    this.setState({
      cloneName: e.target.value || ''
    });
  }

  handleCloneConfirmed = async () => {
    const {
      workflow,
      cloneName
    } = this.state;

    if (!workflow) {
      return;
    }

    this.setState({
      isCloning: true,
      cloneErrorMessage: undefined
    });

    try {
      await cloneWorkflow(workflow.uuid, {
        name: cloneName
      });

      this.setState({
        workflow: undefined,
        shouldShowCloneModal: false,
        isCloning: false,
        cloneErrorMessage: undefined
      });

      this.props.history.push('/workflows/');
    } catch (ex) {
      this.setState({
        cloneErrorMessage: ex.message,
        isCloning: false
      });
    }
  }

  handleCloneCancelled = () => {
    this.setState({
      shouldShowCloneModal: false,
      isCloning: false,
      cloneErrorMessage: undefined
    });
  }

  handleDeletionConfirmed = async () => {
    const {
      workflow
    } = this.state;

    if (!workflow) {
      return;
    }

    this.setState({
      isDeleting: true,
      deletionErrorMessage: undefined
    });

    try {
      await deleteWorkflow(workflow.uuid);
      this.props.history.replace('/workflows');
    } catch (e) {
      this.setState({
        isDeleting: false,
        deletionErrorMessage: `Failed to delete Workflow "${workflow.name}": ${e.message || 'Unknown error'}`
      });
    }
  }

  handleDeletionCancelled = () => {
    this.setState({
      shouldShowDeletionModal: false,
      isDeleting: false,
      deletionErrorMessage: undefined
    });
  }
}

export default withRouter(WorkflowDetail);