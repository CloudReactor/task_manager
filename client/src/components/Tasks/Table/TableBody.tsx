import moment from 'moment';

import * as C from '../../../utils/constants';
import * as path from '../../../constants/routes';

import { TaskImpl } from '../../../types/domain_types';

import React, { Fragment, useContext } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  Tooltip,
  Switch
 } from '@mui/material';


import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import { colorPicker, timeFormat, timeDuration } from '../../../utils/index';
import ActionButton from '../../common/ActionButton';
import Status from '../../Status/Status';
import "../../../styles/tableStyles.scss";


interface Props {
  tasks: TaskImpl[];
  task: TaskImpl | null;
  editTask: (uuid: string, data: any) => Promise<void>;
  handleDeletion: (task: TaskImpl) => void;
  handleActionRequested: (action: string | undefined, cbData: any) => any;
  taskUuidToInProgressOperation: any;
}

const timeOrDuration = (
  item:
    | {
        latest_task_execution: object;
      }
    | any,
  propName: string,
  fallback: string,
  ago: boolean
): string => {
  if (item.latest_task_execution && item.latest_task_execution[propName]) {
    const m = moment(item.latest_task_execution[propName]);
    return ago ? m.fromNow() : timeFormat(m.toDate());
  }
  else {
    return fallback;
  };
}

const TableBody = ({
  tasks,
  handleDeletion,
  handleActionRequested,
  taskUuidToInProgressOperation,
  editTask
}: Props) => {
  const context = useContext(GlobalContext);
  const accessLevel = accessLevelForCurrentGroup(context);
  const isStartAllowed = accessLevel && (accessLevel >= C.ACCESS_LEVEL_TASK);
  const isMutationAllowed = accessLevel && (accessLevel >= C.ACCESS_LEVEL_DEVELOPER);

  const numberFormat = new Intl.NumberFormat();

  const history = useNavigate();

  return (
    <tbody>
      {tasks.map(task => {
        const lte = task.latest_task_execution as any; // hack
        const colors = lte ? colorPicker(lte.status, task.is_service, task.enabled) : '';
        const pushToTaskPage = () =>
          history(`${path.TASKS}/${task.uuid}`, { state: { item: task }});

        const taskInProgressAction =
          taskUuidToInProgressOperation[task.uuid];

        const isStartInProgress = (taskInProgressAction ===
          (task.is_service ? 'enable_service' : 'start'));

        const isStartDisabled = !task.canManuallyStart() ||
          (task.is_service && task.enabled && !isStartInProgress);

        const isStopInProgress = (taskInProgressAction ===
          (task.is_service ? 'disable_service' : 'stop'));

        const isStopDisabled = task.is_service ? !task.enabled :
          (!lte || (C.TASK_EXECUTION_STATUSES_IN_PROGRESS.indexOf(lte.status) < 0));

        return (
          <tr key={task.uuid} className="custom_status_bg">
            <td onClick={pushToTaskPage}>
              {task.name}
            </td>
            <td className="text-center pointer">
              <Tooltip title={(task.enabled ? 'Disable' : 'Enable') + ' this Task'}>
                <Switch color="primary" checked={task.enabled}
                 disabled={!isMutationAllowed}
                 onChange={event => {editTask(task.uuid, { enabled: event.target.checked })}} />
              </Tooltip>
            </td>
            <td onClick={pushToTaskPage}>
              {task.is_service
                ? 'Service'
                : task.schedule
                ? 'Scheduled'
                : 'On-demand'}
            </td>
            <td className={colors} onClick={pushToTaskPage}>
              <Status enabled={task.enabled} isService={task.is_service}
               status={lte?.status} forExecutionDetail={false} />
            </td>
            <td onClick={pushToTaskPage}>
              {timeOrDuration(task, "started_at", "Never started", false)}
            </td>
            <td onClick={pushToTaskPage}>
              {
                !lte
                ? null
                : !lte.finished_at
                ? null
                : timeOrDuration(task, "finished_at", "Not finished", false)
              }
            </td>
            <td onClick={pushToTaskPage}>
              {(lte &&
                `${timeDuration(
                  lte.started_at,
                  lte.finished_at
                )}`)}
            </td>
            <td onClick={pushToTaskPage}>
              {timeOrDuration(task, "last_heartbeat_at", "No heartbeat received", true)}
            </td>
            <td className="text-right pointer" onClick={pushToTaskPage}>
              {
                lte && (typeof lte.success_count === 'number') &&
                numberFormat.format(lte.success_count)
              }
            </td>
            <td  onClick={pushToTaskPage}>
              {task.schedule}
            </td>
            <td className="tableActionsColumn">
              {
                (isMutationAllowed || (isStartAllowed && !task.is_service)) && (
                  <Fragment>
                    <ActionButton
                      cbData={task}
                      onActionRequested={handleActionRequested}
                      action={task.is_service ? 'enable_service' : 'start'}
                      faIconName='play'
                      disabled={isStartDisabled}
                      inProgress={isStartInProgress}
                      tooltip={task.is_service ? 'Enable this service' : 'Start a new Task Execution'}
                    />

                    <ActionButton
                      cbData={task}
                      onActionRequested={handleActionRequested}
                      action={task.is_service ? 'disable_service' : 'stop'}
                      faIconName='stop'
                      disabled={isStopDisabled}
                      tooltip={task.is_service ? 'Disable this service' : 'Stop the latest Task Execution'}
                      inProgress={isStopInProgress}
                      color='secondary'
                    />
                  </Fragment>
                )
              }

              <Tooltip title="Modify Task schedule">
                <i
                  className="fas fa-wrench pl-2 pr-2"
                  onClick={() => handleActionRequested('config', task)}
                />
              </Tooltip>

              {
                isMutationAllowed && (
                  <Tooltip title="Remove Task">
                    <i
                      className="fas fa-trash"
                      onClick={() => handleDeletion(task)}
                    />
                  </Tooltip>
                )
              }
            </td>
          </tr>
        );
      })}
    </tbody>
  );
};

export default TableBody;
