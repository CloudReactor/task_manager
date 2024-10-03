import { AxiosError, isCancel } from 'axios';

import { exceptionToErrorMessages, makeAuthenticatedClient } from '../../../axios_config';
import * as utils from '../../../utils';
import {
  makeEmptyResultsPage,
  fetchRunEnvironments,
  fetchTasks, fetchTasksInErrorCount, updateTask
} from '../../../utils/api'
import { TaskImpl, RunEnvironment } from '../../../types/domain_types';

import React, {Fragment, useCallback, useContext, useEffect, useRef, useState } from 'react';
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
  const [taskPage, setTaskPage] = useState(makeEmptyResultsPage<TaskImpl>());
  const [tasksInErrorCount, setTasksInErrorCount] = useState(0);

  const [loadTasksAbortController, setLoadTasksAbortController] = useState<AbortController | null>(null);
  const [loadTasksInErrorAbortController, setLoadTasksInErrorAbortController] = useState<AbortController | null>(null);
  const [shouldShowConfigModal, setShouldShowConfigModal] = useState(false);
  const [task, setTask] = useState<TaskImpl | null>(null);
  const [selfTimeout, setSelfTimeout] = useState<NodeJS.Timeout | null>(null);
  const [taskUuidToInProgressOperation, setTaskUuidToInProgressOperation] =
    useState<Record<string, string>>({});
  const [lastErrorMessage, setLastErrorMessage] = useState<string | null>(null);
  const [lastLoadErrorMessage, setLastLoadErrorMessage] = useState<string | null>(null);
  const [runEnvironments, setRunEnvironments] = useState<Array<RunEnvironment>>([]);

  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  const mounted = useRef(false);

  //console.log('TaskList: searchParams:', searchParams);

  const loadRunEnvironments = useCallback(async () => {
    setAreRunEnvironmentsLoading(true);
    try {
      const page = await fetchRunEnvironments({
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

    if (loadTasksInErrorAbortController) {
      loadTasksInErrorAbortController.abort('Operation superceded');
    }
    const updatedLoadTasksInErrorAbortController = new AbortController();
    setLoadTasksInErrorAbortController(updatedLoadTasksInErrorAbortController);

    try {
      setTasksInErrorCount(await fetchTasksInErrorCount({
        groupId: currentGroup?.id,
        q,
        runEnvironmentUuids: selectedRunEnvironmentUuids,
        statuses: selectedStatuses,
        abortSignal: updatedLoadTasksInErrorAbortController.signal
      }));

      setLoadTasksInErrorAbortController(null);
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

    //console.log('loadTasks');

    if (loadTasksAbortController) {
      loadTasksAbortController.abort('Operation superceded');
    }

    if (!mounted.current) {
      return;
    }

    const updatedLoadTasksAbortController = new AbortController();
    setLoadTasksAbortController(updatedLoadTasksAbortController);

    if (selfTimeout) {
      clearTimeout(selfTimeout);
      setSelfTimeout(null);
    }

    const {
      q,
      sortBy,
      descending,
      selectedRunEnvironmentUuids,
      selectedStatuses,
      rowsPerPage,
      currentPage,
    } = transformSearchParams(searchParams);

    //console.log('loadTasks: searchParams:', searchParams);
    //console.log('loadTasks: selectedRunEnvironmentUuids:', selectedRunEnvironmentUuids);

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
        abortSignal: updatedLoadTasksAbortController.signal
      });

      if (mounted.current) {
        setLoadTasksAbortController(null);
        setTaskPage(taskPage);
        setAreTasksLoading(false);

        await loadTasksInErrorCount();

        if (mounted.current) {
          //console.log('loadTasks: setSelfTimeout');
          setSelfTimeout(setTimeout(loadTasks, UIC.TASK_REFRESH_INTERVAL_MILLIS));
        }
      }
    } catch (error) {
      if (isCancel(error)) {
        return;
      }

      setLastLoadErrorMessage('Failed to load Tasks');
    } finally {
      setAreTasksLoading(false);
    }
  };

  const handleActionRequested = async (action: string | undefined, cbData: any) => {
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
          await updateTask(uuid, {enabled: true});
          break;

        case 'disable_service':
          errorMessage += ' to disable service';
          await updateTask(uuid, {enabled: false});
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
  };

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

  const handleDeletion = async (task: TaskImpl) => {
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
  };

  const editTask = async (uuid: string, data: any) => {
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
  };

  const handleCloseConfigModal = useCallback(() => {
    setShouldShowConfigModal(false);
  }, []);

  const cleanupLoading = () => {
    if (loadTasksAbortController) {
      loadTasksAbortController.abort('Operation canceled after component unmounted');
    }

    if (loadTasksInErrorAbortController) {
      loadTasksInErrorAbortController.abort('Operation canceled after component unmounted');
    }

    if (selfTimeout) {
      clearTimeout(selfTimeout);
    }
  };

  useEffect(() => {
    mounted.current = true;

    loadRunEnvironments()

    return () => {
      //console.log('TaskList: cleanup on empty list');

      mounted.current = false;

      cleanupLoading();
    };
  }, []);

  useEffect(() => {
    loadTasks();

    return () => {
      cleanupLoading();
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
