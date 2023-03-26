import React, { Component } from 'react';
import { RouteComponentProps, withRouter } from 'react-router';
import { Link } from 'react-router-dom';

import { WorkflowExecution } from '../../../types/domain_types';

import {
  fetchWorkflowExecution, retryWorkflowExecution, stopWorkflowExecution
} from '../../../utils/api'

import * as UIC from '../../../utils/ui_constants';

import BreadcrumbBar from "../../../components/BreadcrumbBar/BreadcrumbBar";
import WorkflowExecutionDetailsTable from '../../../components/WorkflowExecutionDetails/WorkflowExecutionDetailsTable';
import WorkflowExecutionDiagram from '../../../components/WorkflowExecutionDetails/WorkflowExecutionDiagram';
import {
  WORKFLOW_EXECUTION_STATUSES_IN_PROGRESS
} from '../../../utils/constants';
import {shouldRefreshWorkflowExecution} from '../../../utils/domain_utils';
import ActionButton from '../../../components/common/ActionButton';
import styles from './index.module.scss';


type PathParamsType = {
  uuid: string;
};

type Props = RouteComponentProps<PathParamsType>;

interface State {
  workflowExecution: WorkflowExecution | null;
  isStopping: boolean;
  isRetryRequested: boolean;
  interval: any;
}

class WorkflowExecutionDetail extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    this.state = {
      workflowExecution: null,
      isStopping: false,
      isRetryRequested: false,
      interval: null
    };
  }

  async componentDidMount() {
    document.title = 'Task Execution Details';
    await this.fetchExecutionDetails();
  }

  componentWillUnmount() {
    if (this.state.interval) {
      clearInterval(this.state.interval);
    }
  }

  setupRefresh = () => {
    const {
     workflowExecution,
     interval
    } = this.state;

    let updatedInterval = interval;

    if (workflowExecution &&
        shouldRefreshWorkflowExecution(workflowExecution)) {
      if (!interval) {
        updatedInterval = setInterval(this.fetchExecutionDetails,
          UIC.TASK_REFRESH_INTERVAL_MILLIS);
      }
    } else {
       if (interval) {
         clearInterval(interval)
         updatedInterval = null;
       }
    }

    this.setState({
      interval: updatedInterval
    });
  }

  fetchExecutionDetails = async () => {
    const uuid = this.props.match.params.uuid;

    try {
      const workflowExecution = await fetchWorkflowExecution(uuid);

      this.setState({
        workflowExecution
      }, this.setupRefresh);
    } catch (error) {
      console.log(error);
    }
  }

  public render() {
    const {
      workflowExecution,
      isStopping,
      isRetryRequested
    } = this.state;

    if (!workflowExecution) {
      return <div>Loading ...</div>
    }

    const workflowLink = (
        <Link to={`/workflows/${workflowExecution.workflow.uuid}`}>
          {workflowExecution.workflow.name}
        </Link>
    );

    const inProgress = WORKFLOW_EXECUTION_STATUSES_IN_PROGRESS.includes(workflowExecution.status);

    return (
      <div className={styles.container}>
        <BreadcrumbBar
          rootUrl="/workflows" rootLabel="Workflows"
          firstLevel={workflowLink}
          secondLevel={'Execution ' + workflowExecution.uuid}
        />
        <div>
          <ActionButton action="stop" faIconName="stop" label="Stop"
            onActionRequested={this.handleActionRequested}
            inProgress={isStopping} inProgressLabel="Stopping"
            disabled={!inProgress}
          />
          <ActionButton action="retry" faIconName="redo" label="Retry"
            onActionRequested={this.handleActionRequested}
            inProgress={isRetryRequested} inProgressLabel="Retrying"
            disabled={inProgress}
          />
        </div>
        <WorkflowExecutionDetailsTable workflowExecution={workflowExecution} />
        <WorkflowExecutionDiagram workflowExecution={workflowExecution}
          onWorkflowExecutionUpdated={this.handleWorkflowExecutionUpdated}/>
      </div>
    );
  }

  handleWorkflowExecutionUpdated = async (workflowExecutionUuid: string, workflowExecution?: WorkflowExecution) => {
    if (workflowExecution) {
      this.setState({
        workflowExecution
      }, this.setupRefresh);
    } else {
      await this.fetchExecutionDetails();
    }
  }

  handleActionRequested = (action: string | undefined, cbData: any) => {
    const {
      workflowExecution
    } = this.state;

    if (!workflowExecution) {
      return;
    }

    switch (action) {
      case 'stop':
        this.setState({
          isStopping: true
        }, async () => {
          try {
            const we = await stopWorkflowExecution(workflowExecution.uuid);
            this.setState({
              workflowExecution: we,
              isStopping: false
            });
          } catch (e) {
            this.setState({
              isStopping: false
            });
          }
        });
        break;

      case 'retry':
        this.setState({
          isRetryRequested: true
        }, async () => {
          try {
            const we = await retryWorkflowExecution(workflowExecution.uuid);
            this.setState({
              workflowExecution: we,
              isRetryRequested: false
            });
          } catch (e) {
            this.setState({
              isRetryRequested: false
            });
            return;
          }

          this.setupRefresh();
        });
        break;

      default:
        console.error(`Unknown action ${action}`);
        break;
    }

  }
}

export default withRouter(WorkflowExecutionDetail);