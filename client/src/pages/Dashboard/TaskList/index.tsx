import { AxiosError, isCancel } from 'axios';

import { exceptionToErrorMessages, makeAuthenticatedClient } from '../../../axios_config';
import * as C from '../../../utils/constants';
import * as utils from '../../../utils';
import * as api from '../../../utils/api';
import { fetchTasks, ResultsPage, updateTask } from '../../../utils/api'
import { TaskImpl, RunEnvironment } from '../../../types/domain_types';

import React, {Fragment, useCallback, useContext, useEffect, useState } from 'react';
import { useHistory } from 'react-router-dom';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { Alert } from 'react-bootstrap'

import swal from 'sweetalert';

import { GlobalContext } from '../../../context/GlobalContext';
import * as UIC from '../../../utils/ui_constants';
import { getParams, setURL } from '../../../utils/url_search';

import ConfigModalContainer from '../../../components/ConfigModal/ConfigModalContainer';
import ConfigModalBody from '../../../components/ConfigModal/ConfigModalBody';
import FailureCountAlert from '../../../components/common/FailureCountAlert';
import TaskTable from '../../../components/Tasks/TaskTable';
import Onboarding from '../../../components/Tasks/Onboarding/Onboarding';
import Loading from '../../../components/Loading';
import styles from './index.module.scss';

const TaskList = (props: AbortSignalProps) => {
  const {
    abortSignal
  } = props;

  const { currentGroup } = useContext(GlobalContext);

  const [areTasksLoading, setAreTasksLoading] = useState(true);
  const [areRunEnvironmentsLoading, setAreRunEnvironmentsLoading] = useState(false);
  const [taskPage, setTaskPage] = useState(api.makeEmptyResultsPage<TaskImpl>());
  const [shouldShowConfigModal, setShouldShowConfigModal] = useState(false);
  const [task, setTask] = useState<TaskImpl | null>(null);
  const [selfInterval, setSelfInterval] = useState<any>(null);
  const [taskUuidToInProgressOperation, setTaskUuidToInProgressOperation] =
    useState<Record<string, string>>({});
  const [lastErrorMessage, setLastErrorMessage] = useState<string | null>(null);
  const [lastLoadErrorMessage, setLastLoadErrorMessage] = useState<string | null>(null);
  const [runEnvironments, setRunEnvironments] = useState<Array<RunEnvironment>>([]);

  const history = useHistory();

  const loadRunEnvironments = useCallback(async () => {
    setAreRunEnvironmentsLoading(true);
    try {
      const page = await api.fetchRunEnvironments({
        groupId: currentGroup?.id,
        abortSignal
      });

      setRunEnvironments(page.results);
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request canceled: ' + error.message);
      }
    } finally {
      setAreRunEnvironmentsLoading(false);
    }
  }, []);

  const loadTasks = useCallback(async () => {
    // This would cause the search input to lose focus, because it would be
    // temporarily replaced with a loading indicator.
    //setAreTasksLoading(true);
    const {
      q,
      sortBy,
      descending,
      selectedRunEnvironmentUuid,
      rowsPerPage,
      currentPage,
    } = getParams(history.location.search);

    const offset = currentPage * rowsPerPage;

    try {
      const taskPage = await fetchTasks({
        groupId: currentGroup?.id,
        sortBy,
        descending,
        offset,
        maxResults: rowsPerPage,
        q,
        selectedRunEnvironmentUuid,
        abortSignal
      });

      setTaskPage(taskPage);
      setAreTasksLoading(false);
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request canceled: ' + error.message);
        return;
      }

      if (selfInterval) {
        clearInterval(selfInterval);
        setSelfInterval(null);
      }

      setLastLoadErrorMessage('Failed to load Tasks');
    } finally {
      setAreTasksLoading(false);
    }

    return;
  }, []);

  const handleActionRequested = useCallback(async (action: string | undefined, cbData: any) => {
    const cbTask = cbData as TaskImpl;
    if (action === 'config') {
      setTask(cbTask);
      setShouldShowConfigModal(true);
      return;
    }

    const uuid = cbTask.uuid;

    const updatedTaskUuidToInProgressOperation = Object.assign({},
      taskUuidToInProgressOperation);

    if (action) {
      updatedTaskUuidToInProgressOperation[uuid] = action;
    } else {
      delete updatedTaskUuidToInProgressOperation[uuid];
    }

    setTaskUuidToInProgressOperation(updatedTaskUuidToInProgressOperation);
    setLastErrorMessage(null);

    let errorMessage = 'Failed';

    try {
      switch (action) {
        case 'start':
          errorMessage += ' to start Task Execution';
          await utils.startTaskExecution(cbTask);
          break;

        case 'stop':
          if (cbTask?.latest_task_execution) {
            errorMessage += ' to stop Task Execution';
            await utils.stopTaskExecution(cbTask,
              (cbTask.latest_task_execution as any).uuid);
          }
          break;

        case 'enable_service':
          errorMessage += ' to enable service';
          await api.updateTask(uuid, {enabled: true});
          break;

        case 'disable_service':
          errorMessage += ' to disable service';
          await api.updateTask(uuid, {enabled: false});
          break;

        case 'config':
          setShouldShowConfigModal(true);
          break;

        default:
          console.error(`Unknown action '${action}'`);
          break;
      }

      await loadTasks();
    } catch (err) {
      const messages = exceptionToErrorMessages(err);

      if (messages?.length) {
        errorMessage += ': ';
        errorMessage += messages.join('\n');
      }

      setLastErrorMessage(errorMessage);
    } finally {
      const inProgressObj = Object.assign({},
        updatedTaskUuidToInProgressOperation);

      delete inProgressObj[uuid];

      setTaskUuidToInProgressOperation(inProgressObj);
    }
  }, [taskUuidToInProgressOperation]);

  const handleSortChanged = useCallback(async (ordering?: string, toggleDirection?: boolean) => {
    setURL(history.location, history, ordering, 'sort_by');
    loadTasks();
  }, []);

  const handleSelectItemsPerPage = useCallback((
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    setURL(history.location, history, rowsPerPage, 'rows_per_page');
    loadTasks();
  }, []);

  const handleQueryChanged = useCallback((
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const q = event.target.value;
    setURL(history.location, history, q, 'q');
    loadTasks();
  }, []);

  const handleRunEnvironmentChanged = useCallback((
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const selectedRunEnvironmentUuid = event.target.value;
    setURL(history.location, history, selectedRunEnvironmentUuid, 'selected_run_environment_uuid');
    loadTasks();
  }, []);

  const handlePageChanged = useCallback((currentPage: number) => {
    setURL(history.location, history, currentPage + 1, 'page');
    loadTasks();
  }, []);

  /*
  const handlePrev = () => {
    const { currentPage = 0 } = getParams(history.location);
    setURL(history.location, history, currentPage, 'page');
    loadTasks();
  }

  const handleNext = () => {
    const { currentPage = 0 } = getParams(history.location);
    setURL(history.location, history, currentPage + 2, 'page');
    loadTasks();
  } */

  const failedTaskCount = useCallback((tasks: TaskImpl[]): number => {
    let count = 0;
    tasks.forEach(task => {
      if (task.enabled && task.latest_task_execution &&
          (C.TASK_EXECUTION_STATUSES_WITH_PROBLEMS.indexOf(
            (task.latest_task_execution as any).status) >= 0)) {
        count += 1;
      }
    });

    return count;
  }, []);

  const handleDeletion = useCallback(async (uuid: string) => {
    const approveDeletion = await swal({
      title: 'Are you sure you want to delete this Task?',
      buttons: ['no', 'yes'],
      icon: 'warning',
      dangerMode: true
    });

    if (approveDeletion) {
      setLastErrorMessage(null);

      try {
        await makeAuthenticatedClient().delete(`api/v1/tasks/${uuid}/`);
      } catch (err) {
        setLastErrorMessage('Failed to delete Task');
      }

      await loadTasks();
    }
  }, []);

  const editTask = useCallback(async (uuid: string, data: any) => {
    try {
      await updateTask(uuid, data);
      await loadTasks();
    } catch (err) {
      let lastErrorMessage = 'Failed to update Task';

      if ((err instanceof AxiosError) && err.response && err.response.data) {
         lastErrorMessage += ': ' + JSON.stringify(err.response.data);
      }

      setLastErrorMessage(lastErrorMessage);
    }
  }, []);

  const handleCloseConfigModal = useCallback(() => {
    setShouldShowConfigModal(false);
  }, []);

  useEffect(() => {
    loadRunEnvironments()
  }, []);

  useEffect(() => {
    loadTasks().then(_dummy => {
      const interval = setInterval(loadTasks,
        UIC.TASK_REFRESH_INTERVAL_MILLIS);
      setSelfInterval(interval);
    });

    return () => {
      if (selfInterval) {
        clearInterval(selfInterval);
        setSelfInterval(null);
      }
    };
  }, []);

  const {
    q,
    sortBy,
    descending,
    selectedRunEnvironmentUuid,
    rowsPerPage,
    currentPage
  } = getParams(history.location.search);

  const taskTableProps = {
    handleRunEnvironmentChanged,
    handleQueryChanged,
    loadTasks,
    handleSortChanged,
    handlePageChanged,
    handleSelectItemsPerPage,
    handleDeletion,
    handleActionRequested,
    editTask,
    q,
    sortBy,
    descending,
    currentPage,
    rowsPerPage,
    taskPage,
    shouldShowConfigModal,
    task,
    taskUuidToInProgressOperation,
    runEnvironments,
    selectedRunEnvironmentUuid
  };

  return (
    <Fragment>
      {
        areTasksLoading || areRunEnvironmentsLoading
        ? (<Loading />)
        : !runEnvironments.length
          ? (<Onboarding />)
          : (
              <div className={styles.container}>
                <FailureCountAlert itemName="Task" count={failedTaskCount(taskPage.results)} />

                {
                  lastErrorMessage &&
                  <Alert variant="danger">
                    { lastErrorMessage }
                  </Alert>
                }

                {
                  lastLoadErrorMessage &&
                  <Alert variant="warning">
                    { lastLoadErrorMessage }
                  </Alert>
                }

                <TaskTable {...taskTableProps} />

                {
                  task && (
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
                  )
                }
              </div>
            )
      }
    </Fragment>
  );
}

export default abortableHoc(TaskList);
