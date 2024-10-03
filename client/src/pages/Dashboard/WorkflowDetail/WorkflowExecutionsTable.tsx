import _ from 'lodash';
import { isCancel } from 'axios';

import { transformSearchParams, updateSearchParams } from '../../../utils/url_search';
import { catchableToString, colorPicker, timeDuration, timeFormat } from '../../../utils';

import React, { Fragment, useEffect, useState } from 'react';

import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import {
  Form,
  Table
} from 'react-bootstrap';

import TablePagination from '@mui/material/TablePagination';
import DefaultPagination from '../../../components/Pagination/Pagination';

import {
  fetchWorkflowExecutionSummaries,
  makeEmptyResultsPage,
  stopWorkflowExecution,
  retryWorkflowExecution,
  itemsPerPageOptions
} from '../../../utils/api';

import {Workflow, WorkflowExecution, WorkflowExecutionSummary} from '../../../types/domain_types';
import * as C from '../../../utils/constants';
import * as UIC from '../../../utils/ui_constants';


import ActionButton from '../../../components/common/ActionButton';

import { TableColumnInfo } from "../../../types/ui_types";

import Status from '../../../components/Status/Status';
import StatusFilter from "../../../components/common/StatusFilter/StatusFilter";

import "../../../styles/tableStyles.scss";

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

  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const loadWorkflowExecutions = async () => {
    const {
      selectedStatuses,
      sortBy,
      descending,
      rowsPerPage,
      currentPage,
    } = transformSearchParams(searchParams, true, true);

    const offset = currentPage * rowsPerPage;

    try {
      const updatedWorkflowExecutionsPage = await fetchWorkflowExecutionSummaries({
        workflowUuid: workflow.uuid,
        statuses: selectedStatuses,
        sortBy: sortBy ?? 'started_at',
        descending: (sortBy ? descending : true),
        offset,
        maxResults: rowsPerPage,
        abortSignal
      });

      setWorkflowExecutionsPage(updatedWorkflowExecutionsPage);
    } catch (err) {
      if (isCancel(err)) {
        return;
      }

      onActionError('loadWorkflowExecutions', workflow, catchableToString(err));
    }
  };

  const handleSelectedStatusesChanged = (statuses?: string[]) => {
    updateSearchParams(searchParams, setSearchParams, statuses, 'status');
  };

  const handlePageChanged = (currentPage: number) => {
    updateSearchParams(searchParams, setSearchParams, currentPage + 1, 'page');
  };

  const handlePageChangeEvent = (event: React.MouseEvent<HTMLButtonElement> | null, page: number) => {
    updateSearchParams(searchParams, setSearchParams, page + 1, 'page');
  };

  /*
  handlePrev = (): void =>
    this.setState({
      currentPage: this.state.currentPage - 1
    }, this.loadWorkflowExecutions);

  handleNext = (): void =>
    this.setState({
      currentPage: this.state.currentPage + 1
    }, this.loadWorkflowExecutions); */

  const handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ): void => {
    const rowsPerPage = parseInt(event.target.value);
    updateSearchParams(searchParams, setSearchParams, rowsPerPage, 'rows_per_page');
  };

  const handleRowsPerChangeEvent = (
    event: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>
  ): void => {
    const rowsPerPage = parseInt(event.target.value);
    updateSearchParams(searchParams, setSearchParams, rowsPerPage, 'rows_per_page');
  };

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
    loadWorkflowExecutions().then(_dummy => {
      if (selfInterval) {
        clearInterval(selfInterval);
      }

      const interval = setInterval(loadWorkflowExecutions,
        UIC.TASK_REFRESH_INTERVAL_MILLIS);
      setSelfInterval(interval);
    });

    return () => {
      if (selfInterval) {
        clearInterval(selfInterval);
      }
    };
  }, [location]);

  const {
    selectedStatuses,
    sortBy,
    descending,
    rowsPerPage,
    currentPage,
  } = transformSearchParams(searchParams, true, true);

  return (
    <Fragment key="workflowExecutionsTable">
      <div>
        <Form.Label className="mr-3 mt-3 mb-3">Status:</Form.Label>
        <StatusFilter selectedStatuses={selectedStatuses}
          handleSelectedStatusesChanged={handleSelectedStatusesChanged}
          forWorkflows={true} />
      </div>
      {
        (workflowExecutionsPage?.results?.length === 0) ? (
          selectedStatuses ? (
            <p className="my-5">
              No Workflow Executions with the selected status(es) found.
              Try selecting different status(es) or removing the filter.
            </p>
          ) : (
            <h2 className="my-5 text-center">
              This Workflow has not run yet. When it does, you&apos;ll be able to see
              a table of past Workflow Executions here.
            </h2>
          )
        ) : (
          <Fragment>
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
                          updateSearchParams(searchParams, setSearchParams, item.ordering, 'sort_by');
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
                    const colors = colorPicker(we.status, false, workflow.enabled);
                    const pushToDetailPage = () => navigate(`/workflow_executions/${we.uuid}`, { state: { we } });
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
                            ? <Status enabled={true} isService={false} status={we.status}
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
                            disabled={!we || (we.status === C.WORKFLOW_EXECUTION_STATUS_RUNNING)} />
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
          </Fragment>
        )
      }
    </Fragment>
  );
}

export default abortableHoc<Props>(WorkflowExecutionsTable);
