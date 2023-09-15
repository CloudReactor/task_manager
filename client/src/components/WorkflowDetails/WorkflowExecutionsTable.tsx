import _ from 'lodash';

import { getParams, setURL } from '../../utils/url_search';
import { catchableToString, colorPicker, timeDuration, timeFormat } from '../../utils';

import React, { useCallback, useEffect, useState } from 'react';

import { useHistory } from 'react-router-dom';

import abortableHoc, { AbortSignalProps } from '../../hocs/abortableHoc';

import {
  Table
} from 'react-bootstrap';

import TablePagination from '@material-ui/core/TablePagination';
import DefaultPagination from '../Pagination/Pagination';

import {
  fetchWorkflowExecutionSummaries,
  makeEmptyResultsPage,
  stopWorkflowExecution,
  retryWorkflowExecution,
  itemsPerPageOptions
} from '../../utils/api';

import {Workflow, WorkflowExecution, WorkflowExecutionSummary} from '../../types/domain_types';
import * as C from '../../utils/constants';
import * as UIC from '../../utils/ui_constants';


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

interface Props {
  workflow: Workflow,
  onActionError: (action: string, cbData: any, errorMessage: string) => void,
  onWorkflowExecutionUpdated: (workflowExecution: WorkflowExecution) => void
}

interface InternalProps extends Props, AbortSignalProps {
}

const WorkflowExecutionsTable = ({
  workflow,
  onActionError,
  onWorkflowExecutionUpdated,
  abortSignal
}: InternalProps) => {
  const [workflowExecutionsPage, setWorkflowExecutionsPage] = useState(
    makeEmptyResultsPage<WorkflowExecutionSummary>());
  const [workflowExecutionUuidsPendingStop, setWorkflowExecutionUuidsPendingStop] = useState<string []>([]);
  const [workflowExecutionUuidsPendingRetry, setWorkflowExecutionUuidsPendingRetry] = useState<string []>([]);
  const [selfInterval, setSelfInterval] = useState<any>(null);

  const history = useHistory();

  const loadWorkflowExecutions = useCallback(async () => {
    const {
      sortBy,
      descending,
      rowsPerPage,
      currentPage,
    } = getParams(history.location.search);

    const offset = currentPage * rowsPerPage;

    try {
      const updatedWorkflowExecutionsPage = await fetchWorkflowExecutionSummaries(workflow.uuid, sortBy,
        (sortBy ? descending : true), offset, rowsPerPage);

      setWorkflowExecutionsPage(updatedWorkflowExecutionsPage);
    } catch (err) {

      onActionError('loadWorkflowExecutions', workflow, catchableToString(err));
    }
  }, []);

  const handlePageChanged = useCallback((currentPage: number) => {
    setURL(history.location, history, currentPage + 1, 'page');
    loadWorkflowExecutions();
  }, []);

  const handlePageChangeEvent = useCallback((event: React.MouseEvent<HTMLButtonElement> | null, page: number) => {
    setURL(history.location, history, page + 1, 'page');
    loadWorkflowExecutions();
  }, []);

  /*
  handlePrev = (): void =>
    this.setState({
      currentPage: this.state.currentPage - 1
    }, this.loadWorkflowExecutions);

  handleNext = (): void =>
    this.setState({
      currentPage: this.state.currentPage + 1
    }, this.loadWorkflowExecutions); */

  const handleSelectItemsPerPage = useCallback((
    event: React.ChangeEvent<HTMLSelectElement>
  ): void => {
    const rowsPerPage = parseInt(event.target.value);
    setURL(history.location, history, rowsPerPage, 'rows_per_page');
    loadWorkflowExecutions();
  }, []);

  const handleRowsPerChangeEvent = useCallback((
    event: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>
  ): void => {
    const rowsPerPage = parseInt(event.target.value);
    setURL(history.location, history, rowsPerPage, 'rows_per_page');
    loadWorkflowExecutions();
  }, []);

  const handleActionRequested = async (action: string | undefined, cbData: any) => {
    switch (action) {
      case 'stop': {
        const updated = workflowExecutionUuidsPendingStop.concat(['' + cbData.uuid]);
        setWorkflowExecutionUuidsPendingStop(updated);

        try {
          const stoppedWorkflowExecution = await stopWorkflowExecution(cbData.uuid);

          onWorkflowExecutionUpdated(stoppedWorkflowExecution);

          setWorkflowExecutionUuidsPendingStop(
              _.pull(workflowExecutionUuidsPendingStop,
                  stoppedWorkflowExecution.uuid)
          );
        } catch (err) {
          onActionError(action, cbData, catchableToString(err));
        }
        await loadWorkflowExecutions();
      }
      break;

      case 'retry': {
        const updated = workflowExecutionUuidsPendingRetry.concat(['' + cbData.uuid]);
        setWorkflowExecutionUuidsPendingRetry(updated);

        try {
          const retriedWorkflowExecution = await retryWorkflowExecution(cbData.uuid);

          onWorkflowExecutionUpdated(retriedWorkflowExecution);

          setWorkflowExecutionUuidsPendingRetry(
              _.pull(workflowExecutionUuidsPendingRetry,
                  retriedWorkflowExecution.uuid)
          );
        } catch (err) {
          onActionError(action, cbData, catchableToString(err));
        }
        await loadWorkflowExecutions();
      }
      break;

      default:
      console.error(`Unknown action: "${action}"`);
      break;
    }
  }

  useEffect(() => {
    const loadExecutions = async () => {
      await loadWorkflowExecutions();
      const interval = setInterval(loadWorkflowExecutions,
        UIC.TASK_REFRESH_INTERVAL_MILLIS);
      setSelfInterval(interval);
    };

    loadExecutions();

    return () => {
      if (selfInterval) {
        clearInterval(selfInterval);
      }
    };
  }, []);

  if (workflowExecutionsPage.results.length === 0) {
    return <div>This Workflow has not run yet.</div>
  }

  const {
    sortBy,
    descending,
    rowsPerPage,
    currentPage,
  } = getParams(history.location.search);

  return (
    <div>
      <DefaultPagination
        currentPage={currentPage}
        pageSize={rowsPerPage}
        count={workflowExecutionsPage.count}
        handleClick={handlePageChanged}
        handleSelectItemsPerPage={handleSelectItemsPerPage}
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
                    const {
                      descending
                    } = getParams(history.location.search);
                    setURL(history.location, history, 1, 'page');
                    setURL(history.location, history, item.ordering, 'sort_by');
                    setURL(history.location, history, !descending, 'descending');

                    await loadWorkflowExecutions();
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
                    <ActionButton cbData={we} onActionRequested={handleActionRequested}
                      action="stop" faIconName="stop" label="Stop"
                      inProgress={workflowExecutionUuidsPendingStop.indexOf(we.uuid) >= 0}
                      inProgressLabel="Stopping ..."
                      disabled={we.status !== C.WORKFLOW_EXECUTION_STATUS_RUNNING} />

                    <ActionButton cbData={we} action="retry" faIconName="redo" label="Retry"
                      onActionRequested={handleActionRequested}
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
          onPageChange={handlePageChangeEvent}
          onRowsPerPageChange={handleRowsPerChangeEvent}
          rowsPerPageOptions={[25, 50, 100]}
        />
      </div>
    </div>
  );
}

export default abortableHoc<Props>(WorkflowExecutionsTable);
