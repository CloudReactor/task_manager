import _ from 'lodash';

import { AxiosError, isCancel } from 'axios';

import * as C from '../../../utils/constants'

import {
  RunEnvironment,
  TaskImpl, TaskExecution
} from '../../../types/domain_types';

import {
  fetchRunEnvironment,
  fetchTask,
  fetchTaskExecutions,
  itemsPerPageOptions,
  makeEmptyResultsPage,
  updateTask
} from '../../../utils/api';

import { transformSearchParams, updateSearchParams } from '../../../utils/url_search';

import {
  catchableToString,
  startTaskExecution,
  stopTaskExecution
} from '../../../utils';

import React, { Fragment, useCallback, useContext, useEffect, useState } from 'react';
import { useLocation, useParams, useSearchParams } from 'react-router-dom';

import { Alert } from 'react-bootstrap';

import TablePagination from '@mui/material/TablePagination';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { BootstrapVariant } from '../../../types/ui_types';
import * as UIC from '../../../utils/ui_constants';

import Charts from './Charts';
import TaskNotificationsTab from '../../../components/TaskNotificationMethods/TaskNotificationsTab';
import TaskSettings from '../../../components/TaskSettings/TaskSettings';
import TaskLinks from '../../../components/TaskLinks/TaskLinks';
import TaskSummary from '../../../components/TaskSummary/TaskSummary';

import DefaultPagination from '../../../components/Pagination/Pagination';
import ConfigModalContainer from '../../../components/ConfigModal/ConfigModalContainer';
import ConfigModalBody from '../../../components/ConfigModal/ConfigModalBody';
import Tabs from '../../../components/common/Tabs';
import '../../../components/Tasks/style.scss';
import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import ActionButton from '../../../components/common/ActionButton';

import { Switch, Tooltip } from '@mui/material';
import styles from './index.module.scss'
import TaskExecutionTable from './TaskExecutionTable';

type PathParamsType = {
  uuid: string;
};

type Props = AbortSignalProps;

const TAB_EXECUTIONS = 'executions';

const TaskDetail = ({
  abortSignal
}: Props) => {
  const [isLoading, setLoading] = useState(false);
  const [task, setTask] = useState<TaskImpl | null>(null);
  const [runEnvironment, setRunEnvironment] = useState<RunEnvironment | null>(null);
  const [lastErrorMessage, setLastErrorMessage] = useState<string | null>(null);
  const [flashAlertVariant, setFlashAlertVariant] = useState<BootstrapVariant>('info');
  const [isStarting, setStarting] = useState(false);

  const [taskExecutionsPage, setTaskExecutionsPage] = useState(
    makeEmptyResultsPage<TaskExecution>());
  const [shouldShowConfigModal, setShouldShowConfigModal] = useState(false);
  const [stoppingTaskExecutionUuids, setStoppingTaskExecutionUuids] =
    useState(new Set<string>());
  const [selfInterval, setSelfInterval] = useState<any>(null);

  const context = useContext(GlobalContext);
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  const {
    uuid
  }  = useParams<PathParamsType>();

  if (!uuid) {
    return <div>Invalid UUID</div>;
  }

  const selectedTab = searchParams.get('tab') ?? TAB_EXECUTIONS;

  const handleActionRequested = async (action: string | undefined, cbData: any): Promise<void> => {
    if (!task) {
      return;
    }

    setLastErrorMessage(null);

    switch (action) {
      case 'configure':
        openConfigModal();
        break;

      case 'start':
        try {
          await startTaskExecution(cbData, (confirmed: boolean) => {
            if (confirmed) {
              setStarting(true);
            }
          });

          loadTaskExecutions();
        } catch (err) {
          setLastErrorMessage('Failed to start Task: ' +
            catchableToString(err));
        } finally {
          setStarting(false);
        }
        break;

      case 'stop':
        try {
          await stopTaskExecution(task, cbData.uuid, (confirmed: boolean) => {
            if (confirmed) {
              const updatedSet = new Set(stoppingTaskExecutionUuids);
              updatedSet.add(cbData.uuid);
              setStarting(true);
              setStoppingTaskExecutionUuids(updatedSet);
            }
          });
        } catch (err) {
          setLastErrorMessage('Failed to stop Task Execution: ' +
            catchableToString(err));
        } finally {
          const updatedSet = new Set(stoppingTaskExecutionUuids);
          updatedSet.delete(cbData.uuid);

          setStoppingTaskExecutionUuids(updatedSet);
        }
        await loadTaskExecutions();
        break;

      default:
        console.error(`Unknown action: "${action}"`);
        break;
    }
  };

  const loadTask = async () => {
    if (task) {
      return task;
    }

    setLoading(false); // CHECKME
    setLastErrorMessage(null);

    try {
      // TODO: omit the latest task execution
      const fetchedTask = await fetchTask(uuid, abortSignal);

      setTask(fetchedTask);
      setLastErrorMessage(null);

      document.title = `CloudReactor - Task ${fetchedTask.name}`;

      return fetchedTask;
    } catch (err) {
      if (!isCancel(err)) {
        setLastErrorMessage('Failed to load Task. It may have been removed previously.');
      }
      return null;
    } finally {
      setLoading(false);
    }
  };

  const loadRunEnvironment = useCallback(async (t: TaskImpl) => {
    if (!t || runEnvironment) {
      return;
    }

    try {
      const fetchedRunEnvironment = await fetchRunEnvironment(
        t.run_environment.uuid, abortSignal);
      setRunEnvironment(fetchedRunEnvironment);
    } catch (err) {
      if (!isCancel(err)) {
        setFlashAlertVariant('danger');
        setLastErrorMessage('Failed to load Run Environment.');
      }
    }
  }, [runEnvironment]);

  const handleSort = async (sortBy: string) => {
    updateSearchParams(searchParams, setSearchParams, sortBy, 'sort_by');
  }

  const loadTaskExecutions = async () => {
    const {
      selectedStatuses,
      sortBy,
      descending,
      rowsPerPage,
      currentPage,
    } = transformSearchParams(searchParams, false, true);

    const offset = currentPage * rowsPerPage;

    const finalSortBy = sortBy ?? 'started_at';
    const finalDescending = descending ?? !sortBy;

    try {
      const taskExecutionsPage = await fetchTaskExecutions({
        taskUuid: uuid,
        statuses: selectedStatuses,
        sortBy: finalSortBy,
        descending: finalDescending,
        offset,
        maxResults: rowsPerPage,
        abortSignal
      });

      setTaskExecutionsPage(taskExecutionsPage);
    } catch (error) {
      if (!isCancel(error)) {
        console.log(error);
      }
    }
  }

  const handleSelectedStatusesChanged = (statuses?: string[]) => {
    updateSearchParams(searchParams, setSearchParams, statuses, 'status');
  }

  const handlePageChanged = (updatedCurrentPage: number) => {
    updateSearchParams(searchParams, setSearchParams, updatedCurrentPage + 1, 'page');
  };

  const handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    updateSearchParams(searchParams, setSearchParams, rowsPerPage, 'rows_per_page');
  };

  const handleCloseConfigModal = () => {
    setShouldShowConfigModal(false);
  };

  const openConfigModal = () => {
    setShouldShowConfigModal(true);
  };

  const handleTaskSubmitted = async (uuid: string, data: any) => {
    try {
      const updatedTask = await updateTask(uuid, data, abortSignal);
      setFlashAlertVariant('success');
      setLastErrorMessage('Updated Task settings');
      setTask(updatedTask);
    } catch (err) {
      if (isCancel(err)) {
        return;
      }

      let errorMessage = 'Failed to update settings';
      if ((err instanceof AxiosError) && err.response && err.response.data) {
         errorMessage += ': ' + JSON.stringify(err.response.data) + ' ' + JSON.stringify(err.response.status);
      }
      setFlashAlertVariant('danger'),
      setLastErrorMessage(errorMessage);
    }
  }

  const handleTabChange = (selectedTabLabel: string) => {
    const value = _.snakeCase(selectedTabLabel ?? TAB_EXECUTIONS);
    setSearchParams(oldSearchParams => {
      if (value === TAB_EXECUTIONS) {
        oldSearchParams.delete('tab');
      } else {
        oldSearchParams.set('tab', value);
      }
      return oldSearchParams;
    }, { replace: true });
  };

  useEffect(() => {
    loadTask().then(t => {
      if (t) {
        loadRunEnvironment(t);
        loadTaskExecutions().then(() => {
          if (selfInterval) {
            clearInterval(selfInterval);
          }
          const interval = setInterval(loadTaskExecutions,
            UIC.TASK_REFRESH_INTERVAL_MILLIS);
          setSelfInterval(interval);
        });
      }
    });

    return () => {
      if (selfInterval) {
        clearInterval(selfInterval);
      }
    };
  }, [location]);

  if (isLoading) {
    return <div>Loading ...</div>
  }

  const name = task?.name;

  const accessLevel = accessLevelForCurrentGroup(context);
  const isStartAllowed = !!accessLevel && (accessLevel >= C.ACCESS_LEVEL_TASK);
  const isMutationAllowed = accessLevel && (accessLevel >= C.ACCESS_LEVEL_DEVELOPER);

  const navItems = ['Executions', 'Settings', 'Notifications'];

  return (
    <div className={styles.container}>
      {
        lastErrorMessage &&
        <Alert
          variant={flashAlertVariant || "danger"}
          onClose={() => {
            setLastErrorMessage(null);
          }}
          dismissible
        >
          { lastErrorMessage }
        </Alert>
      }

      {
        task && (
          <Fragment>
            <div className={styles.breadcrumbContainer}>
              <BreadcrumbBar
                firstLevel={name}
                secondLevel={null}
              />

              <div>
                <Tooltip title={(task.enabled ? 'Disable' : 'Enable') + ' this Task'}>
                  <Switch
                    color="primary"
                    checked={task.enabled}
                    disabled={!isMutationAllowed}
                    className={styles.switch}
                    onChange={event => {
                      handleTaskSubmitted(
                        task.uuid,
                        { enabled: event.target.checked }
                      )}
                    }
                  />
                </Tooltip>
                <ActionButton cbData={task} onActionRequested={handleActionRequested}
                  action="configure" faIconName="wrench" label="Schedule"
                  tooltip={ (isMutationAllowed ? 'Modify' : 'View') + " this Task's run schedule" } />

                <ActionButton cbData={task} onActionRequested={handleActionRequested}
                  action="start" disabled={!isStartAllowed || !task.canManuallyStart()} inProgress={isStarting}
                  faIconName="play" label="Start" inProgressLabel="Starting ..."
                  tooltip={ isStartAllowed ? (
                    task.canManuallyStart() ?
                      'Start a new Execution of this Task' :
                      'This Task cannot be manually started'
                  ) : 'You do not have permission to manually start this Task' } />
              </div>
            </div>

            <TaskSummary task={task} />

            <TaskLinks links={task.links} />
            <div>
              <Tabs selectedTab={selectedTab} navItems={navItems} onTabChange={handleTabChange} />
            </div>
            <div>
              {(() => {
                switch (selectedTab) {
                  case 'settings':
                    return <TaskSettings task={task} runEnvironment={runEnvironment ?? undefined} />;
                  case 'notifications':
                    return <TaskNotificationsTab task={task} onTaskSaved={handleTaskSubmitted} />;
                  default: {
                    const {
                      selectedStatuses,
                      sortBy,
                      descending,
                      rowsPerPage,
                      currentPage,
                    } = transformSearchParams(searchParams, false, true);

                    const maxCurrentPage = (taskExecutionsPage.count / rowsPerPage);
                    const adjustedCurrentPage = Math.min(currentPage, maxCurrentPage);

                    return (
                      <Fragment>
                        <Charts task={task} />
                        <DefaultPagination
                          currentPage={adjustedCurrentPage}
                          pageSize={rowsPerPage}
                          count={taskExecutionsPage.count}
                          handleClick={handlePageChanged}
                          handleSelectItemsPerPage={handleSelectItemsPerPage}
                          itemsPerPageOptions={itemsPerPageOptions}
                        />
                        <TaskExecutionTable
                          taskExecutions={taskExecutionsPage.results}
                          task={task}
                          onStopRequested={handleActionRequested}
                          stoppingTaskExecutionUuids={stoppingTaskExecutionUuids}
                          selectedStatuses={selectedStatuses}
                          handleSelectedStatusesChanged={handleSelectedStatusesChanged}
                          handleSort={handleSort}
                          sortBy={sortBy}
                          descending={descending}
                        />
                        {
                          (taskExecutionsPage.count > 0) && (
                            <TablePagination
                              component="div"
                              labelRowsPerPage="Showing "
                              count={taskExecutionsPage.count}
                              rowsPerPage={rowsPerPage}
                              page={adjustedCurrentPage}
                              onPageChange={(event) => null}
                            />
                          )
                        }
                      </Fragment>
                    );
                  }
                }
              })()}
            </div>
            <ConfigModalContainer
              isOpen={shouldShowConfigModal}
              handleClose={handleCloseConfigModal}
              title={task.name}
            >
              <ConfigModalBody
                task={task}
                editTask={handleTaskSubmitted}
                handleClose={handleCloseConfigModal}
              />
            </ConfigModalContainer>
          </Fragment>
        )
      }
    </div>
  );
}

export default abortableHoc(TaskDetail);
