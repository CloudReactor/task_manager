import { AxiosError, isCancel } from 'axios';

import { exceptionToErrorMessages, makeAuthenticatedClient } from '../../../axios_config';
import * as utils from '../../../utils';
import * as api from '../../../utils/api';
import { fetchTasks, fetchTasksInErrorCount, updateTask } from '../../../utils/api'
import { TaskImpl, RunEnvironment } from '../../../types/domain_types';

import React, {Fragment, useCallback, useContext, useEffect, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { Alert } from 'react-bootstrap'

import { create } from 'react-modal-promise';

import { GlobalContext } from '../../../context/GlobalContext';
import * as UIC from '../../../utils/ui_constants';
import { transformSearchParams, updateSearchParams } from '../../../utils/url_search';

import AsyncConfirmationModal from '../../../components/common/AsyncConfirmationModal';
import ConfigModalContainer from '../../../components/ConfigModal/ConfigModalContainer';
import ConfigModalBody from '../../../components/ConfigModal/ConfigModalBody';
import FailureCountAlert from '../../../components/common/FailureCountAlert';
import TaskTable from '../../../components/Tasks/TaskTable';
import Onboarding from '../../../components/Tasks/Onboarding/Onboarding';
import Loading from '../../../components/Loading';
import styles from './index.module.scss';

const TaskList = ({
  abortSignal
}: AbortSignalProps) => {
  const { currentGroup } = useContext(GlobalContext);

  const [areTasksLoading, setAreTasksLoading] = useState(true);
  const [areRunEnvironmentsLoading, setAreRunEnvironmentsLoading] = useState(false);
  const [taskPage, setTaskPage] = useState(api.makeEmptyResultsPage<TaskImpl>());
  const [tasksInErrorCount, setTasksInErrorCount] = useState(0);
  const [shouldShowConfigModal, setShouldShowConfigModal] = useState(false);
  const [task, setTask] = useState<TaskImpl | null>(null);
  const [selfInterval, setSelfInterval] = useState<any>(null);
  const [taskUuidToInProgressOperation, setTaskUuidToInProgressOperation] =
    useState<Record<string, string>>({});
  const [lastErrorMessage, setLastErrorMessage] = useState<string | null>(null);
  const [lastLoadErrorMessage, setLastLoadErrorMessage] = useState<string | null>(null);
  const [runEnvironments, setRunEnvironments] = useState<Array<RunEnvironment>>([]);

  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

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

  const loadTasksInErrorCount = async () => {
    const {
      q,
      selectedRunEnvironmentUuids,
      selectedStatuses
    } = transformSearchParams(searchParams);

    try {
      setTasksInErrorCount(await fetchTasksInErrorCount({
        groupId: currentGroup?.id,
        q,
        runEnvironmentUuids: selectedRunEnvironmentUuids,
        statuses: selectedStatuses,
        abortSignal
      }));
    } catch (error) {
      if (!isCancel(error)) {
        //console.('Request canceled: ' + error.message);
        return;
      }
    }
  };

  const loadTasks = async () => {
    // This would cause the search input to lose focus, because it would be
    // temporarily replaced with a loading indicator.
    //setAreTasksLoading(true);

    const {
      q,
      sortBy,
      descending,
      selectedRunEnvironmentUuids,
      selectedStatuses,
      rowsPerPage,
      currentPage,
    } = transformSearchParams(searchParams);

    const offset = currentPage * rowsPerPage;

    try {
      const taskPage = await fetchTasks({
        groupId: currentGroup?.id,
        sortBy: sortBy ?? 'name',
        descending: descending ?? false,
        offset,
        maxResults: rowsPerPage,
        q,
        runEnvironmentUuids: selectedRunEnvironmentUuids,
        statuses: selectedStatuses,
        abortSignal
      });

      setTaskPage(taskPage);
      setAreTasksLoading(false);

      await loadTasksInErrorCount();
    } catch (error) {
      if (isCancel(error)) {
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
  };

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

  const handleSortChanged = async (sortBy?: string, toggleDirection?: boolean) => {
    updateSearchParams(searchParams, setSearchParams, sortBy, 'sort_by');
  };

  const handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    updateSearchParams(searchParams, setSearchParams, rowsPerPage, 'rows_per_page');
  };

  const handleQueryChanged = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const q = event.target.value;
    updateSearchParams(searchParams, setSearchParams, q, 'q');
  };

  const handleSelectedRunEnvironmentUuidsChanged = (
    selectedRunEnvironmentUuids?: string[]
  ) => {
    updateSearchParams(searchParams, setSearchParams, selectedRunEnvironmentUuids,
      'run_environment__uuid');
  };

  const handleSelectedStatusesChanged = (
    statuses?: string[]
  ) => {
    updateSearchParams(searchParams, setSearchParams, statuses, 'latest_task_execution__status');
  };

  const handlePageChanged = (currentPage: number) => {
    updateSearchParams(searchParams, setSearchParams, currentPage + 1, 'page');
  };

  const handleDeletion = useCallback(async (task: TaskImpl) => {
    const modal = create(AsyncConfirmationModal);

    const approveDeletion = await modal({
      title: 'Confirm Task Deletion',
      confirmLabel: 'Delete',
      faIconName: 'trash',
      children: (
        <p>
          Are you sure you want to delete Task &lsquo;{task.name}&rsquo;?
        </p>
      )
    });

    if (approveDeletion) {
      setLastErrorMessage(null);

      try {
        await makeAuthenticatedClient().delete(`api/v1/tasks/${task.uuid}/`);
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
      if (selfInterval) {
        clearInterval(selfInterval);
      }

      const interval = setInterval(loadTasks,
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
    q,
    sortBy,
    descending,
    selectedRunEnvironmentUuids,
    selectedStatuses,
    rowsPerPage,
    currentPage,
  } = transformSearchParams(searchParams);

  const finalSortBy = (sortBy ?? 'name');
  const finalDescending = descending ?? false;

  const taskTableProps = {
    handleSelectedRunEnvironmentUuidsChanged,
    handleSelectedStatusesChanged,
    handleQueryChanged,
    loadTasks,
    handleSortChanged,
    handlePageChanged,
    handleSelectItemsPerPage,
    handleDeletion,
    handleActionRequested,
    editTask,
    q,
    sortBy: finalSortBy,
    descending: finalDescending,
    currentPage,
    rowsPerPage,
    taskPage,
    shouldShowConfigModal,
    task,
    taskUuidToInProgressOperation,
    runEnvironments,
    selectedRunEnvironmentUuids,
    selectedStatuses
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
                <FailureCountAlert itemName="Task" count={tasksInErrorCount} />

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
