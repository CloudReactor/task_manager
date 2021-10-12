import _ from 'lodash';

import React, { Component } from 'react';
import {RouteComponentProps, withRouter} from 'react-router';

import {
  Table
} from 'react-bootstrap';

import TablePagination from '@material-ui/core/TablePagination';
import DefaultPagination from '../Pagination/Pagination';

import {
  fetchWorkflowExecutionSummaries,
  stopWorkflowExecution,
  retryWorkflowExecution,
  itemsPerPageOptions,
  ResultsPage
} from '../../utils/api';

import {Workflow, WorkflowExecution, WorkflowExecutionSummary} from '../../types/domain_types';
import * as C from '../../utils/constants';
import * as UIC from '../../utils/ui_constants';
import {colorPicker, timeDuration, timeFormat} from '../../utils';

import ActionButton from '../../components/common/ActionButton';

import { TableColumnInfo } from "../../types/ui_types";

import Status from '../Status/Status'
import {WORKFLOW_EXECUTION_STATUS_RUNNING} from '../../utils/constants';
import "../../styles/tableStyles.scss";

const WORKFLOW_EXECUTION_COLUMNS: TableColumnInfo[] = [
  { name: 'Started', ordering: 'started_at' },
  { name: 'Finished', ordering: 'finished_at' },
  { name: 'Run Duration', ordering: '' },
  { name: 'Status', ordering: 'status' },
  { name: 'Failed Attempts', ordering: 'failed_attempts', textAlign: 'text-right' },
  { name: 'Timed Out Attempts', ordering: 'timed_out_attempts', textAlign: 'text-right' },
  { name: 'Actions', ordering: '' }
];

type PathParamsType = {
};

interface Props extends RouteComponentProps<PathParamsType> {
  workflow: Workflow,
  onActionError: (action: string, cbData: any, errorMessage: string) => void,
  onWorkflowExecutionUpdated: (workflowExecution: WorkflowExecution) => void
}

interface State {
  workflowExecutionsPage: ResultsPage<WorkflowExecutionSummary>;
  currentPage: number;
  rowsPerPage: number;
  sortBy: string;
  descending: boolean;
  selectedExecution: WorkflowExecutionSummary | null;
  workflowExecutionUuidsPendingStop: string[],
  workflowExecutionUuidsPendingRetry: string[],
  interval: any;
}

class WorkflowExecutionsTable extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    this.state = {
      workflowExecutionsPage: { count: 0, results: [] },
      currentPage: 0,
      rowsPerPage: UIC.DEFAULT_PAGE_SIZE,
      sortBy: 'started_at',
      descending: true,
      selectedExecution: null,
      workflowExecutionUuidsPendingStop: [],
      workflowExecutionUuidsPendingRetry: [],
      interval: null
    };
  }

  async componentDidMount() {
    await this.loadWorkflowExecutions();
    const interval = setInterval(this.loadWorkflowExecutions,
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

  handleActionRequested = async (action: string | undefined, cbData: any): Promise<void> => {
    const {
      onActionError,
      onWorkflowExecutionUpdated
    } = this.props;

    let {
      workflowExecutionUuidsPendingStop,
      workflowExecutionUuidsPendingRetry
    } = this.state;

    switch (action) {
      case 'stop':
        this.setState({
          workflowExecutionUuidsPendingStop:
            workflowExecutionUuidsPendingStop.concat(['' + cbData.uuid])
        });

        try {
          const stoppedWorkflowExecution = await stopWorkflowExecution(cbData.uuid);

          onWorkflowExecutionUpdated(stoppedWorkflowExecution);

          this.setState({
            workflowExecutionUuidsPendingStop:
              _.pull(this.state.workflowExecutionUuidsPendingStop,
                  stoppedWorkflowExecution.uuid)
          });
        } catch (e) {
          onActionError(action, cbData, e.message);
        }
        await this.loadWorkflowExecutions();
        break;

      case 'retry':
        this.setState({
          workflowExecutionUuidsPendingRetry:
            workflowExecutionUuidsPendingRetry.concat(['' + cbData.uuid])
        });

        try {
          const retriedWorkflowExecution = await retryWorkflowExecution(cbData.uuid);

          onWorkflowExecutionUpdated(retriedWorkflowExecution);

          this.setState({
            workflowExecutionUuidsPendingRetry:
              _.pull(this.state.workflowExecutionUuidsPendingRetry,
                  retriedWorkflowExecution.uuid)
          });
        } catch (e) {
          onActionError(action, cbData, e.message);
        }
        await this.loadWorkflowExecutions();
        break;

      default:
        console.error(`Unknown action: "${action}"`);
        break;
    }
  }

  loadWorkflowExecutions = async (ordering?: string,
                                  toggleDirection?: boolean) => {
    const {
      workflow,
      onActionError
    } = this.props;

    const {
      currentPage,
      rowsPerPage
    } = this.state;

    let {
      sortBy,
      descending
    } = this.state;

    sortBy = ordering || sortBy;

    if (toggleDirection) {
      descending = !descending;
    }

    const offset = currentPage * rowsPerPage;

    try {
      const workflowExecutionsPage = await fetchWorkflowExecutionSummaries(workflow.uuid, sortBy,
        descending, offset, rowsPerPage);

      this.setState({
        descending,
        workflowExecutionsPage,
        sortBy
      });
    } catch (err) {
      onActionError('loadWorkflowExecutions', workflow, err.message);
    }
  }

  handlePageChanged = (currentPage: number): void => {
    this.setState({ currentPage }, this.loadWorkflowExecutions);
  }

  handlePrev = (): void =>
    this.setState({
      currentPage: this.state.currentPage - 1
    }, this.loadWorkflowExecutions);

  handleNext = (): void =>
    this.setState({
      currentPage: this.state.currentPage + 1
    }, this.loadWorkflowExecutions);

  handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ): void => {
    const value: any = event.target.value;
    this.setState({
      rowsPerPage: parseInt(value)
    }, this.loadWorkflowExecutions);
  };

  public render() {
    const {
      history
    } = this.props;

    const {
      workflowExecutionsPage,
      currentPage,
      rowsPerPage,
      sortBy,
      descending,
      workflowExecutionUuidsPendingStop,
      workflowExecutionUuidsPendingRetry
    } = this.state;

    if (workflowExecutionsPage.results.length === 0) {
      return <div>This Workflow has not run yet.</div>
    }

    return (
      <div>
        <DefaultPagination
          currentPage={currentPage}
          pageSize={rowsPerPage}
          count={workflowExecutionsPage.count}
          handleClick={this.handlePageChanged}
          handleSelectItemsPerPage={this.handleSelectItemsPerPage}
          itemsPerPageOptions={itemsPerPageOptions}
        />
        <Table striped bordered responsive hover size="sm">
          <thead>
            <tr>
              {WORKFLOW_EXECUTION_COLUMNS.map(
                (item: TableColumnInfo) => (
                  <th
                    key={item.name}
                    onClick={item.ordering ? async () => {
                      await this.loadWorkflowExecutions(item.ordering, true)
                    } : undefined
                  }
                    className={'th-header' + (item.textAlign ? ` ${item.textAlign}`: '')}
                  >
                    {item.name}
                    {
                      (sortBy === item.ordering) &&
                      <span>
                        &nbsp;
                        <i className={'fas fa-arrow-' + (descending ?  'down' : 'up')} />
                      </span>

                    }
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {workflowExecutionsPage.results.map(
              (
                we: WorkflowExecutionSummary,
                index: number
              ) => {
                // isService: TODO
                const colors = colorPicker(we.status, false);
                const pushToDetailPage = () => history.push(`/workflow_executions/${we.uuid}`, { we });
                return (
                  <tr key={index} className="custom_status_bg">
                    <td onClick={pushToDetailPage}>
                      {we.started_at ? timeFormat(we.started_at) : "Never started"}
                    </td>
                    <td onClick={pushToDetailPage}>
                      {we.finished_at ? timeFormat(we.finished_at) : "Not finished"}
                    </td>
                    <td onClick={pushToDetailPage}>
                      {timeDuration(we.started_at, we.finished_at)}
                    </td>
                    <td className={colors} onClick={pushToDetailPage}>
                      {we
                        ? <Status isService={false} status={we.status}
                           forExecutionDetail={true} />
                        : null}
                    </td>
                    <td className="text-right" onClick={pushToDetailPage}>
                      {we.failed_attempts}
                    </td>
                    <td className="text-right" onClick={pushToDetailPage}>
                      {we.timed_out_attempts}
                    </td>
                    <td>
                      <ActionButton cbData={we} onActionRequested={this.handleActionRequested}
                       action="stop" faIconName="stop" label="Stop"
                       inProgress={workflowExecutionUuidsPendingStop.indexOf(we.uuid) >= 0}
                       inProgressLabel="Stopping ..."
                       disabled={we.status !== C.WORKFLOW_EXECUTION_STATUS_RUNNING} />

                      <ActionButton cbData={we} action="retry" faIconName="redo" label="Retry"
                       onActionRequested={this.handleActionRequested}
                       inProgress={workflowExecutionUuidsPendingRetry.indexOf(we.uuid) >= 0}
                       inProgressLabel="Retrying ..."
                       disabled={!we || (we.status === WORKFLOW_EXECUTION_STATUS_RUNNING)} />
                    </td>
                  </tr>
                );
              }
            )}
          </tbody>
        </Table>
        <div className="d-flex justify-content-between align-items-center">
          <TablePagination
            component="div"
            labelRowsPerPage="Showing "
            count={workflowExecutionsPage.count}
            rowsPerPage={rowsPerPage}
            page={currentPage}
            onChangePage={() => null}
            onChangeRowsPerPage={() => null}
          />
        </div>
      </div>
    );
  }
}

export default withRouter(WorkflowExecutionsTable);
