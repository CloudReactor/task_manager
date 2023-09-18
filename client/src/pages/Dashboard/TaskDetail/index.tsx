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
  ResultsPage,
  updateTask
} from '../../../utils/api';

import { getParams, setURL } from '../../../utils/url_search';

import {
  catchableToString,
  startTaskExecution,
  stopTaskExecution
} from '../../../utils';

import React, { Fragment, useCallback, useContext, useEffect, useState } from 'react';
import { useHistory, useParams } from 'react-router-dom';

import { Alert } from 'react-bootstrap';

import TablePagination from '@material-ui/core/TablePagination';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { BootstrapVariant } from '../../../types/ui_types';
import * as UIC from '../../../utils/ui_constants';

import Charts from './Charts';
import TaskAlerts from '../../../components/TaskAlerts/TaskAlerts';
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

import { Switch } from '@material-ui/core';
import styles from './index.module.scss'
import TaskExecutionTable from './TaskExecutionTable';

type PathParamsType = {
  uuid: string;
};

type Props = AbortSignalProps;

interface State {
  isLoading: boolean;
  taskExecutionsPage: ResultsPage<TaskExecution>;
  shouldShowConfigModal: boolean;
  task?: TaskImpl;
  runEnvironment?: RunEnvironment,
  interval?: any;
  isStarting: boolean;
  stoppingTaskExecutionUuids: Set<string>;
  lastErrorMessage: string | null;
  selectedTab: string;
  flashAlertVariant?: BootstrapVariant;
}

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
  const [selectedTab, setSelectedTab] = useState('overview');
  const [selfInterval, setSelfInterval] = useState<any>(null);

  const context = useContext(GlobalContext);
  const history = useHistory();

  const {
    uuid
  }  = useParams<PathParamsType>();

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
    setLoading(false); // CHECKME
    setLastErrorMessage(null);

    try {
      const fetchedTask = await fetchTask(uuid, abortSignal);

      setTask(fetchedTask);
      setLastErrorMessage(null);

      document.title = `CloudReactor - Task ${fetchedTask.name}`;

      return fetchedTask;
    } catch (err) {
      setLastErrorMessage('Failed to load Task. It may have been removed previously.');
      return null;
    } finally {
      setLoading(false);
    }
  };

  const loadRunEnvironment = async (t: TaskImpl) => {
    if (!t) {
      return;
    }

    try {
      const runEnvironment = await fetchRunEnvironment(
        t.run_environment.uuid, abortSignal);
      setRunEnvironment(runEnvironment);
    } catch (err) {
      setFlashAlertVariant('danger');
      setLastErrorMessage('Failed to load Run Environment.');
    }
  }

  const handleSort = async (sortBy: string) => {
    setURL(history.location, history, sortBy, 'sort_by');
    await loadTaskExecutions();
  }

  const loadTaskExecutions = async () => {
    const {
      sortBy,
      descending,
      rowsPerPage,
      currentPage,
    } = getParams(history.location.search);

    const offset = currentPage * rowsPerPage;

    const finalSortBy = sortBy ?? 'started_at';
    const finalDescending = descending ?? !sortBy;

    try {
      const taskExecutionsPage = await fetchTaskExecutions({
        taskUuid: uuid,
        sortBy: finalSortBy,
        descending: finalDescending,
        offset,
        maxResults: rowsPerPage,
        abortSignal
      });

      setTaskExecutionsPage(taskExecutionsPage);
    } catch (error) {
      // TODO: show alert
      console.log(error);
    }
  }

  const handlePageChanged = (updatedCurrentPage: number) => {
    setURL(history.location, history, updatedCurrentPage + 1, 'page');
    loadTaskExecutions();
  };

  const handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    setURL(history.location, history, rowsPerPage, 'rows_per_page');
    loadTaskExecutions();
  };

  const handleCloseConfigModal = () => {
    setShouldShowConfigModal(false);
  };

  const openConfigModal = () => {
    setShouldShowConfigModal(true);
  };

  const editTask = async (uuid: string, data: any) => {
    try {
      const updatedTask = await updateTask(uuid, data, abortSignal);
      setFlashAlertVariant('success');
      setLastErrorMessage('Updated Task settings');
      setTask(updatedTask);

      history.push("#", { item: updatedTask })
    } catch (err) {
      if (isCancel(err)) {
        console.log("Request canceled: " + err.message);
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

  const onTabChange = (selectedTab: string) => {
    setSelectedTab(selectedTab.toLowerCase());
  }

  useEffect(() => {
    loadTask().then(t => {
      if (t) {
        loadRunEnvironment(t);
        loadTaskExecutions().then(() => {
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
  }, []);

  if (isLoading) {
    return <div>Loading ...</div>
  }

  const name = task?.name;

  const accessLevel = accessLevelForCurrentGroup(context);
  const isStartAllowed = !!accessLevel && (accessLevel >= C.ACCESS_LEVEL_TASK);
  const isMutationAllowed = accessLevel && (accessLevel >= C.ACCESS_LEVEL_DEVELOPER);

  const navItems = ['Overview', 'Settings', 'Alerts'];

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
                <Switch
                  color="primary"
                  checked={task.enabled}
                  disabled={!isMutationAllowed}
                  className={styles.switch}
                  onChange={event => {
                    editTask(
                      task.uuid,
                      { enabled: event.target.checked }
                    )}
                  }
                />
                <ActionButton cbData={task} onActionRequested={handleActionRequested}
                  action="configure" faIconName="wrench" label="Configuration"
                  tooltip={ (isMutationAllowed ? 'Modify' : 'View') + " this Task's configuration" } />

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
              <Tabs selectedTab={selectedTab} navItems={navItems} onTabChange={onTabChange} />
            </div>
            <div>
              {(() => {
                const {
                  sortBy,
                  descending,
                  rowsPerPage,
                  currentPage,
                } = getParams(history.location.search);

                switch (selectedTab) {
                  case 'settings':
                    return <TaskSettings task={task} runEnvironment={runEnvironment ?? undefined} />;
                  case 'alerts':
                    return <TaskAlerts task={task} editTask={editTask} />;
                  default:
                    return (
                      (taskExecutionsPage.count > 0) ? (
                        <Fragment>
                          <Charts id={uuid} history={history} />
                          <h2 className="mt-5">Executions</h2>

                          <DefaultPagination
                            currentPage={currentPage}
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
                            handleSort={handleSort}
                            sortBy={sortBy}
                            descending={descending}
                          />
                          <TablePagination
                            component="div"
                            labelRowsPerPage="Showing"
                            count={taskExecutionsPage.count}
                            rowsPerPage={rowsPerPage}
                            page={currentPage}
                            onPageChange={(event) => null}
                          />
                        </Fragment>
                      ) : (
                        <h2 className="my-5 text-center">
                          This Task has not run yet. When it does, you&apos;ll be able to see
                          a table of past Task Executions here.
                        </h2>
                      )
                    );
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
                editTask={editTask}
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
