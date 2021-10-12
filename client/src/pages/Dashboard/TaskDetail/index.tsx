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
  ResultsPage,
  updateTask
} from '../../../utils/api';

import { stopTaskExecution, startTaskExecution } from '../../../utils/index';

import React, { Component, Fragment } from 'react';
import { withRouter, RouteComponentProps } from 'react-router';

import { Alert } from 'react-bootstrap';

import TablePagination from '@material-ui/core/TablePagination';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

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
  id: string;
};

type Props = RouteComponentProps<PathParamsType> & {
};

interface State {
  isLoading: boolean;
  taskExecutionsPage: ResultsPage<TaskExecution>;
  currentPage: number;
  rowsPerPage: number;
  sortBy: string;
  descending: boolean;
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

class TaskDetail extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    this.state = {
      isLoading: false,
      taskExecutionsPage: { count: 0, results: [] },
      currentPage: 0,
      rowsPerPage: UIC.DEFAULT_PAGE_SIZE,
      sortBy: 'started_at',
      descending: true,
      shouldShowConfigModal: false,
      isStarting: false,
      stoppingTaskExecutionUuids: new Set(),
      lastErrorMessage: null,
      selectedTab: 'overview'
    };
  }

  async componentDidMount() {
    await this.loadTask();
    await this.loadRunEnvironment()
    await this.loadTaskExecutions();
    const interval = setInterval(this.loadTaskExecutions,
      UIC.TASK_REFRESH_INTERVAL_MILLIS);
    this.setState({
      interval
    });
  }

  componentWillUnmount() {
    if (this.state.interval) {
      clearInterval(this.state.interval);
    }
  }

  handleActionRequested = async (action: string | undefined, cbData: any): Promise<void> => {
    const {
      task: process
    } = this.state;

    if (!process) {
      return;
    }

    this.setState({
      lastErrorMessage: null
    });

    switch (action) {
      case 'configure':
        this.openConfigModal();
        break;

      case 'start':
        try {
          await startTaskExecution(cbData, (confirmed: boolean) => {
            if (confirmed) {
              this.setState({
                isStarting: true
              });
            }
          });

          this.loadTaskExecutions();
        } catch (err) {
          this.setState({
            lastErrorMessage: err.message || 'Failed to start Task'
          });
        } finally {
          this.setState({
            isStarting: false
          });
        }
        break;

      case 'stop':
        try {
          await stopTaskExecution(process, cbData.uuid, (confirmed: boolean) => {
            if (confirmed) {
              const {
                stoppingTaskExecutionUuids
              } = this.state;

              const updatedSet = new Set(stoppingTaskExecutionUuids);
              updatedSet.add(cbData.uuid);

              this.setState({
                isStarting: true,
                stoppingTaskExecutionUuids: updatedSet
              });
            }
          });
        } catch (err) {
          this.setState({
            lastErrorMessage: 'Failed to stop Task Execution' || err.message
          });
        } finally {
          const {
            stoppingTaskExecutionUuids
          } = this.state;

          const updatedSet = new Set(stoppingTaskExecutionUuids);
          updatedSet.delete(cbData.uuid);

          this.setState({
            stoppingTaskExecutionUuids: updatedSet
          });
        }
        await this.loadTaskExecutions();
        break;

      default:
        console.error(`Unknown action: "${action}"`);
        break;
    }
  }

  async loadTask() {
    this.setState({
      isLoading: false,
      lastErrorMessage: null
    });

    const uuid = this.props.match.params.id;

    try {
      const task = await fetchTask(uuid);

      this.setState({ task, lastErrorMessage: null });

      document.title = `CloudReactor - Task ${task.name}`;
    } catch (err) {

      this.setState({
        lastErrorMessage: 'Failed to load Task. It may have been removed previously.'
      });
    }
  }

  async loadRunEnvironment() {
    const {
      task
    } = this.state;

    if (!task) {
      return;
    }

    try {
      const runEnvironment = await fetchRunEnvironment(task.run_environment.uuid);
      this.setState({ runEnvironment });
    } catch (err) {

      this.setState({
        lastErrorMessage: 'Failed to load Run Environment.'
      });
    }
  }

  loadTaskExecutions = async (ordering?: string, toggleDirection?: boolean) => {
    const {
      currentPage,
      rowsPerPage
    } = this.state;

    let {
      sortBy,
      descending
    } = this.state;

    sortBy = ordering || sortBy;

    if (toggleDirection) {
      descending = !descending;
    }

    const offset = currentPage * rowsPerPage;

    try {
      const taskExecutionsPage = await fetchTaskExecutions({
        taskUuid: this.props.match.params.id,
        sortBy,
        descending,
        offset,
        maxResults: rowsPerPage
      });

      this.setState({
        descending,
        taskExecutionsPage,
        sortBy
      });
    } catch (error) {
      console.log(error);
    }
  }

  handlePageChanged = (currentPage: number): void => {
    this.setState({ currentPage }, this.loadTaskExecutions);
  }

  handlePrev = (): void =>
    this.setState({
      currentPage: this.state.currentPage - 1
    }, this.loadTaskExecutions);

  handleNext = (): void =>
    this.setState({
      currentPage: this.state.currentPage + 1
    }, this.loadTaskExecutions);

  handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ): void => {
    const value: any = event.target.value;
    this.setState({
      rowsPerPage: parseInt(value)
    }, this.loadTaskExecutions);
  };

  handleCloseConfigModal = () => {
    this.setState({
      shouldShowConfigModal: false
    });
  };

  openConfigModal = () => {
    this.setState({
      shouldShowConfigModal: true
    })
  }

  editTask = async (uuid: string, data: any): Promise<void> => {
    try {
      const task = await updateTask(uuid, data)
      this.setState({
        flashAlertVariant: 'success',
        lastErrorMessage: 'Updated Task settings'
      });
      this.setState({ task: task }, () =>
        this.props.history.push("#", { item: task })
      );
    } catch (err) {
      let errorMessage = 'Failed to update settings';
      if (err.response && err.response.data) {
         errorMessage += ': ' + JSON.stringify(err.response.data) + ' ' + JSON.stringify(err.response.status);
      }
      this.setState({
        flashAlertVariant: 'danger',
        lastErrorMessage: errorMessage
      })
    }
  }

  onTabChange = (selectedTab: string) => {
    const value = selectedTab.toLowerCase();
    this.setState({
      selectedTab: value
    });
  }

  public render() {
    const {
      isLoading,
      currentPage,
      rowsPerPage,
      descending,
      sortBy,
      stoppingTaskExecutionUuids,
      task,
      runEnvironment,
      taskExecutionsPage,
      isStarting,
      shouldShowConfigModal,
      lastErrorMessage,
      selectedTab,
      flashAlertVariant
    } = this.state;

    if (isLoading) {
      return <div>Loading ...</div>
    }

    const name = task?.name;

    const accessLevel = accessLevelForCurrentGroup(this.context);
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
              this.setState({
                lastErrorMessage: null
              });
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
                      this.editTask(
                        task.uuid,
                        { enabled: event.target.checked }
                      )}
                    }
                  />
                  <ActionButton cbData={task} onActionRequested={this.handleActionRequested}
                    action="configure" faIconName="wrench" label="Configuration"
                    tooltip={ (isMutationAllowed ? 'Modify' : 'View') + " this Task's configuration" } />

                  <ActionButton cbData={task} onActionRequested={this.handleActionRequested}
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
                <Tabs selectedTab={selectedTab} navItems={navItems} onTabChange={this.onTabChange} />
              </div>
              <div>
                {(() => {
                  switch (selectedTab) {
                    case 'settings':
                      return <TaskSettings task={task} runEnvironment={runEnvironment} />;
                    case 'alerts':
                      return <TaskAlerts task={task} editTask={this.editTask} />;
                    default:
                      return (
                        (taskExecutionsPage.count > 0) ? (
                          <Fragment>
                            <Charts id={this.props.match.params.id} history={this.props.history} />
                            <h2 className="mt-5">Executions</h2>

                            <DefaultPagination
                              currentPage={currentPage}
                              pageSize={rowsPerPage}
                              count={taskExecutionsPage.count}
                              handleClick={this.handlePageChanged}
                              handleSelectItemsPerPage={this.handleSelectItemsPerPage}
                              itemsPerPageOptions={itemsPerPageOptions}
                            />
                            <TaskExecutionTable
                              taskExecutions={taskExecutionsPage.results}
                              task={task}
                              onStopRequested={this.handleActionRequested}
                              stoppingTaskExecutionUuids={stoppingTaskExecutionUuids}
                              handleSort={this.loadTaskExecutions}
                              sortBy={sortBy}
                              descending={descending}
                            />
                            <TablePagination
                              component="div"
                              labelRowsPerPage="Showing"
                              count={taskExecutionsPage.count}
                              rowsPerPage={rowsPerPage}
                              page={currentPage}
                              onChangePage={() => null}
                              onChangeRowsPerPage={() => null}
                            />
                          </Fragment>
                        ) : (
                          <h2 className="my-5 text-center">
                            This Task has not run yet. When it does, you'll be able to see
                            a table of past executions here.
                          </h2>
                        )
                      );
                  }
                })()}
              </div>
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
            </Fragment>
          )
        }
      </div>
    );
  }
}

export default withRouter(TaskDetail);
