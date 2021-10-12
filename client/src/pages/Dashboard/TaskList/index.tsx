import _ from 'lodash';
import axios from 'axios';

import { exceptionToErrorMessages, makeAuthenticatedClient } from '../../../axios_config';
import * as C from '../../../utils/constants';
import * as utils from '../../../utils';
import * as api from '../../../utils/api';
import { fetchTasks, ResultsPage, updateTask } from '../../../utils/api'
import { TaskImpl, RunEnvironment } from '../../../types/domain_types';

import React, {Component, Fragment} from 'react';
import { withRouter, RouteComponentProps } from "react-router";
import cancelTokenHoc, { CancelTokenProps } from '../../../hocs/cancelTokenHoc';

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

interface Props extends RouteComponentProps<any> {
};

interface State {
  areTasksLoading: boolean;
  areRunEnvironmentsLoading: boolean;
  taskPage: ResultsPage<TaskImpl>;
  shouldShowConfigModal: boolean;
  task: TaskImpl | null;
  interval: any;
  taskUuidToInProgressOperation: any;
  lastErrorMessage: string | null;
  lastLoadErrorMessage: string | null;
  runEnvironments: RunEnvironment[];
}

type InnerProps = Props & CancelTokenProps;

class TaskList extends Component<InnerProps, State> {
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      areTasksLoading: true,
      areRunEnvironmentsLoading: true,
      taskPage: { count: 0, results: [] },
      shouldShowConfigModal: false,
      task: null,
      interval: null,
      taskUuidToInProgressOperation: {},
      lastErrorMessage: null,
      lastLoadErrorMessage: null,
      runEnvironments: [],
    };

    this.loadTasks = _.debounce(this.loadTasks, 250);
  }

  async componentDidMount() {
    await this.loadTasks();
    await this.loadRunEnvironments();
    const interval = setInterval(this.loadTasks,
      UIC.TASK_REFRESH_INTERVAL_MILLIS);
    this.setState({
      interval,
    });
  }

  componentWillUnmount() {
    if (this.state.interval) {
      clearInterval(this.state.interval);
    }
  }

  async loadRunEnvironments() {
    const {
      cancelToken
    } = this.props;

    const { currentGroup } = this.context;

    try {
      const page = await api.fetchRunEnvironments({
        groupId: currentGroup?.id,
        cancelToken
      });
      this.setState({
        runEnvironments: page.results,
        areRunEnvironmentsLoading: false,
      });
    } catch (error) {
      if (axios.isCancel(error)) {
        console.log('Request cancelled: ' + error.message);
        return;
      }
    }
  }

  private handleActionRequested = async (action: string | undefined, cbData: any): Promise<void> => {
    const task = cbData as TaskImpl;
    if (action === 'config') {
      this.setState({
        task: task,
        shouldShowConfigModal: true
      });
      return;
    }

    const uuid = task.uuid;

    const {
      taskUuidToInProgressOperation
    } = this.state;

    const updatedTaskUuidToInProgressOperation = Object.assign({},
        taskUuidToInProgressOperation);
    updatedTaskUuidToInProgressOperation[uuid] = action;

    this.setState({
      taskUuidToInProgressOperation: updatedTaskUuidToInProgressOperation,
      lastErrorMessage: null
    });

    let errorMessage = 'Failed';

    try {
      switch (action) {
        case 'start':
          errorMessage += ' to start Task Execution';
          await utils.startTaskExecution(task);
          break;

        case 'stop':
          if (task?.latest_task_execution) {
            errorMessage += ' to stop Task Execution';
            await utils.stopTaskExecution(task,
              (task.latest_task_execution as any).uuid);
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
          this.setState({
            shouldShowConfigModal: true
          });
          break;

        default:
          console.error(`Unknown action '${action}'`);
          break;
      }

      return this.loadTasks();
    } catch (err) {
      const messages = exceptionToErrorMessages(err);

      if (messages?.length) {
        errorMessage += ': ';
        errorMessage += messages.join('\n');
      }

      this.setState({
        lastErrorMessage: errorMessage
      });
    } finally {
      const inProgressObj = Object.assign({},
        updatedTaskUuidToInProgressOperation);

      delete inProgressObj[uuid];

      this.setState({
        taskUuidToInProgressOperation: inProgressObj
      });
    }
  }

  private handleSortChanged = async (ordering?: string, toggleDirection?: boolean) => {
    setURL(this.props.location, this.props.history, ordering, 'sort_by')
    this.loadTasks();
  };

  private loadTasks = async () => {
    // get query params (if any) from url -- to load process types with
    const {
      q,
      sortBy,
      descending,
      selectedRunEnvironmentUuid,
      rowsPerPage = UIC.DEFAULT_PAGE_SIZE,
      currentPage = 0,
    } = getParams(this.props.location.search);

    const offset = currentPage * rowsPerPage;

    const { currentGroup } = this.context;

    try {
      const taskPage = await fetchTasks({
        groupId: currentGroup?.id,
        sortBy,
        descending,
        offset,
        maxResults: rowsPerPage,
        q,
        selectedRunEnvironmentUuid,
        cancelToken: this.props.cancelToken
      });

      this.setState({
        taskPage: taskPage,
        areTasksLoading: false,
      });
    } catch (error) {
      if (axios.isCancel(error)) {
        console.log('Request cancelled: ' + error.message);
        return;
      }
      this.setState({
        lastLoadErrorMessage: 'Failed to load Tasks'
      });
    }
  }

  handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ): void => {
    setURL(this.props.location, this.props.history, parseInt(event.target.value), 'rows_per_page');
    this.loadTasks();
  };

  handleQueryChanged = (
    event: React.ChangeEvent<HTMLInputElement>
  ): void => {
    setURL(this.props.location, this.props.history, event.target.value, 'q');
    this.loadTasks();
  };

  handleRunEnvironmentChanged = (
    event: React.ChangeEvent<HTMLInputElement>
  ): void => {
    setURL(this.props.location, this.props.history, event.target.value, 'selected_run_environment_uuid');
    this.loadTasks();
  };

  handlePageChanged = (currentPage: number): void => {
    setURL(this.props.location, this.props.history, currentPage + 1, 'page');
    this.loadTasks();
  }

  handlePrev = (): void => {
    const { currentPage = 0 } = getParams(this.props.location);
    setURL(this.props.location, this.props.history, currentPage, 'page');
    this.loadTasks();
  }

  handleNext = (): void => {
    const { currentPage = 0 } = getParams(this.props.location);
    setURL(this.props.location, this.props.history, currentPage + 2, 'page');
    this.loadTasks();
  }

  failedTaskCount = (tasks: TaskImpl[]): number => {
    let count = 0;
    tasks.forEach(task => {
      if (task.enabled && task.latest_task_execution &&
          (C.TASK_EXECUTION_STATUSES_WITH_PROBLEMS.indexOf(
            (task.latest_task_execution as any).status) >= 0)) {
        count += 1;
      }
    });

    return count;
  };

  private handleDeletion = async (uuid: string) => {
    const approveDeletion = await swal({
      title: 'Are you sure you want to delete this Task?',
      buttons: ['no', 'yes'],
      icon: 'warning',
      dangerMode: true
    });

    if (approveDeletion) {
      this.setState({
        lastErrorMessage: null
      });

      try {
        await makeAuthenticatedClient().delete(`api/v1/tasks/${uuid}/`);
      } catch (err) {
        this.setState({
          lastErrorMessage: 'Failed to delete Task'
        });
      }

      return this.loadTasks();
    }
  };

  private editTask = async (uuid: string, data: any) => {
    try {
      await updateTask(uuid, data);
      this.loadTasks();
    } catch (err) {
      let lastErrorMessage = 'Failed to update Task';

      if (err.response && err.response.data) {
         lastErrorMessage += ': ' + JSON.stringify(err.response.data);
      }

      this.setState({
        lastErrorMessage
      });
    }
  };

  handleCloseConfigModal = () => {
    this.setState({
      shouldShowConfigModal: false
    });
  };

  renderTaskTable() {
    const {
      lastLoadErrorMessage,
      lastErrorMessage,
      task,
      taskPage,
      shouldShowConfigModal
    } = this.state;

    const failedProcessCount = this.failedTaskCount(taskPage.results);

    // initialise page based on URL query parameters. Destructure with defaults, otherwise typescript throws error
    const {
      q = '',
      sortBy = '',
      descending = false,
      selectedRunEnvironmentUuid = '',
      rowsPerPage = UIC.DEFAULT_PAGE_SIZE,
      currentPage = 0,
    } = getParams(this.props.location.search);

    return (
      <div className={styles.container}>
        <FailureCountAlert itemName="Task" count={failedProcessCount} />

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

        <TaskTable
          handleRunEnvironmentChanged={this.handleRunEnvironmentChanged}
          handleQueryChanged={this.handleQueryChanged}
          loadTasks={this.loadTasks}
          handleSortChanged={this.handleSortChanged}
          handlePageChanged={this.handlePageChanged}
          handleSelectItemsPerPage={this.handleSelectItemsPerPage}
          handleDeletion={this.handleDeletion}
          handleActionRequested={this.handleActionRequested}
          editTask={this.editTask}
          selectedRunEnvironmentUuid={selectedRunEnvironmentUuid}
          q={q}
          sortBy={sortBy}
          descending={descending}
          rowsPerPage={rowsPerPage}
          currentPage={currentPage}
          {...this.state}
        />
        {
          task && (
            <ConfigModalContainer
              isOpen={shouldShowConfigModal}
              handleClose={this.handleCloseConfigModal}
              title={task.name}
            >
              <ConfigModalBody
                task={task}
                editTask={this.editTask}
                handleClose={this.handleCloseConfigModal}
              />
            </ConfigModalContainer>
          )
        }
      </div>
    );
  }

  public render() {

    return (
      <Fragment>
        {
          this.state.areTasksLoading || this.state.areRunEnvironmentsLoading
          ? (<Loading />)
          : !this.state.runEnvironments.length
            ? (<Onboarding />)
            : this.renderTaskTable()
        }
      </Fragment>
    );
  }
}

export default withRouter(cancelTokenHoc(TaskList));