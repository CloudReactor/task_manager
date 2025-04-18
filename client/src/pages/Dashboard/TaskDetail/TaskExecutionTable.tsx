import moment from 'moment';

import * as C from '../../../utils/constants'
import * as path from '../../../constants/routes';
import { Task, TaskExecution } from '../../../types/domain_types';
import { colorPicker, timeFormat, timeDuration } from '../../../utils/index';

import React, { Fragment, useContext } from 'react';
import { useNavigate } from 'react-router-dom';

import { Form, Table } from 'react-bootstrap';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import Status from '../../../components/Status/Status'
import StatusFilter from "../../../components/common/StatusFilter/StatusFilter";
import ActionButton from '../../../components/common/ActionButton';

import '../../../styles/tableStyles.scss';
import { TableColumnInfo } from '../../../types/ui_types';

interface Props {
  taskExecutions: TaskExecution[];
  task: Task,
  stoppingTaskExecutionUuids: Set<string>,
  onStopRequested: (action: string | undefined, taskExecution: any) => any;
  selectedStatuses?: string[];
  handleSelectedStatusesChanged: (statuses?: string[]) => void;
  handleSort: (sortBy: string) => void;
  sortBy: string  | undefined;
  descending: boolean | undefined;
}

const TaskExecutionTable = ({
  taskExecutions, task,
  stoppingTaskExecutionUuids,
  onStopRequested,
  selectedStatuses, handleSelectedStatusesChanged,
  handleSort, sortBy, descending
}: Props) => {
  const context = useContext(GlobalContext);

  const accessLevel = accessLevelForCurrentGroup(context);
  const isMutationAllowed = accessLevel && (accessLevel >= C.ACCESS_LEVEL_TASK);

  const history = useNavigate();

  const numberFormat = new Intl.NumberFormat();

  const TASK_EXECUTION_COLUMNS: TableColumnInfo[] = [
    { name: 'Started', ordering: 'started_at' },
    { name: 'Finished', ordering: 'finished_at' },
    { name: 'Run Duration', ordering: 'duration' },
    { name: 'Status', ordering: 'status' },
    { name: 'Last Heartbeat', ordering: 'last_heartbeat_at' },
    { name: 'Exit Code', ordering: 'exit_code', textAlign: 'text-right' },
    { name: 'Last Status Message', ordering: 'last_status_message' },
    { name: 'Failed Attempts', ordering: 'failed_attempts', textAlign: 'text-right' },
    { name: 'Commit', ordering: 'task_version_signature' },
    { name: 'Processed', ordering: 'success_count', textAlign: 'text-right' },
    { name: 'Errors', ordering: 'error_count', textAlign: 'text-right' },
    { name: 'Skipped', ordering: 'skipped_count', textAlign: 'text-right'  }
  ];

  if (isMutationAllowed) {
    TASK_EXECUTION_COLUMNS.push({ name: 'Actions', ordering: '' });
  }

  return (
    <Fragment key="taskExecutionTable">
    <div>
      <Form inline>
        <Form.Group>
          <Form.Label className="mr-3 mt-3 mb-3">Status:</Form.Label>
          <StatusFilter selectedStatuses={selectedStatuses}
           onSelectedStatusesChanged={handleSelectedStatusesChanged} />
        </Form.Group>
      </Form>
    </div>
    {
      (taskExecutions.length === 0) ? (
        selectedStatuses ? (
          <p className="my-5">
            No Task Executions with the selected status(es) found.
            Try selecting different status(es) or removing the filter.
          </p>
        ) : (
          <h2 className="my-5 text-center">
            This Task has not run yet. When it does, you&apos;ll be able to see
            a table of past Task Executions here.
          </h2>
        )
      ) : (
        <Table striped bordered responsive hover size="sm">
          <thead>
            <tr>
              {TASK_EXECUTION_COLUMNS.map(
                (item: TableColumnInfo) => (
                  <th
                    key={item.name}
                    onClick={item.ordering ? () => {
                      handleSort(item.ordering);
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
          <tbody className="bg-grey">
          {taskExecutions.map(
            (
              taskExecution: TaskExecution,
              index: number
            ) => {
              const colors = colorPicker(taskExecution.status, task.is_service, task.enabled);
              const pushToDetailPage = () => history(
                path.TASK_EXECUTIONS + '/' + taskExecution.uuid, { state: { taskExecution }});
              return (
                <tr key={index} className="custom_status_bg">
                  <td onClick={pushToDetailPage}>
                    {taskExecution.started_at ? timeFormat(taskExecution.started_at) : 'Never started'}
                  </td>
                  <td onClick={pushToDetailPage}>
                    {taskExecution.finished_at ? timeFormat(taskExecution.finished_at) : 'Not finished'}
                  </td>
                  <td onClick={pushToDetailPage}>
                    {timeDuration(taskExecution.started_at, taskExecution.finished_at)}
                  </td>
                  <td className={colors} onClick={pushToDetailPage}>
                    <Status enabled={true} isService={task.is_service}
                    status={taskExecution && taskExecution.status}
                    forExecutionDetail={true} />
                  </td>
                  <td onClick={pushToDetailPage}>
                    {taskExecution.last_heartbeat_at ? moment(taskExecution.last_heartbeat_at).fromNow() : 'No heartbeat received'}
                  </td>

                  <td className="text-right" onClick={pushToDetailPage}>
                    {taskExecution.exit_code}
                  </td>
                  <td onClick={pushToDetailPage}>
                    {taskExecution.last_status_message}
                  </td>
                  <td className="text-right" onClick={pushToDetailPage}>
                    {numberFormat.format(taskExecution.failed_attempts)}
                  </td>
                  <td>
                    {
                      taskExecution.task_version_signature && (
                        <a
                          className="link"
                          target="_blank"
                          href={taskExecution.commit_url || "#"}
                          rel="noopener noreferrer"
                        >
                          {taskExecution.task_version_signature.substring(0, 7)}
                        </a>
                      )
                    }
                  </td>
                  <td className="text-right" onClick={pushToDetailPage}>
                    {
                      ((typeof taskExecution.success_count) === 'number') && numberFormat.format(taskExecution.success_count)
                    }
                  </td>
                  <td className="text-right" onClick={pushToDetailPage}>
                    {
                      ((typeof taskExecution.error_count) === 'number') && numberFormat.format(taskExecution.error_count)
                    }
                  </td>
                  <td className="text-right" onClick={pushToDetailPage}>
                    {
                      ((typeof taskExecution.skipped_count) === 'number') && numberFormat.format(taskExecution.skipped_count)
                    }
                  </td>
                  {
                    isMutationAllowed && (
                      <td>
                        <ActionButton cbData={taskExecution} onActionRequested={onStopRequested}
                          action="stop" faIconName="stop" label="Stop"
                          disabled={C.TASK_EXECUTION_STATUSES_IN_PROGRESS.indexOf(taskExecution.status) < 0}
                          inProgress={stoppingTaskExecutionUuids.has(taskExecution.uuid)}
                          inProgressLabel="Stopping"
                          color="secondary"
                          tooltip="Stop this Task Execution" />
                      </td>
                    )
                  }
                </tr>
              );
            }
          )}
          </tbody>
        </Table>
      )
    }
    </Fragment>
  );
}

export default TaskExecutionTable;
