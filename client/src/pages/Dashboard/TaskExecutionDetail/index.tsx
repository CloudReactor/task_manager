import * as path from '../../../constants/routes';

import { TaskExecution } from '../../../types/domain_types';

import * as UIC from '../../../utils/ui_constants';
import { fetchTaskExecution } from '../../../utils/api';

import React, { Component } from "react";
import { withRouter, RouteComponentProps } from "react-router";
import { Link } from 'react-router-dom'

import { Row, Col } from 'react-bootstrap';

import BreadcrumbBar from "../../../components/BreadcrumbBar/BreadcrumbBar";
import TaskExecutionDetails from "../../../components/TaskExecutionDetails/TaskExecutionDetails";

import styles from './index.module.scss';
import {TASK_EXECUTION_STATUSES_IN_PROGRESS} from '../../../utils/constants';

type PathParamsType = {
  uuid: string;
};

type Props = RouteComponentProps<PathParamsType>;

interface State {
  taskExecution?: TaskExecution;
  interval: any;
}

class TaskExecutionDetail extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    this.state = {
      interval: null
    };
  }

  componentDidMount() {
    document.title = 'Task Execution Details';
    this.fetchExecutionDetails();
    const interval = setInterval(this.fetchExecutionDetails,
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

  fetchExecutionDetails = async () => {
    const {
      interval
    } = this.state;

    const uuid = this.props.match.params.uuid;

    try {
      const taskExecution = await fetchTaskExecution(uuid);

      this.setState({
        taskExecution
      });

      if (interval &&
          !TASK_EXECUTION_STATUSES_IN_PROGRESS.includes(taskExecution.status)) {
        clearInterval(interval);
        this.setState({
          interval: null
        });
      }
    } catch (error) {
      console.log(error);
    }
  }


  public render() {
    const {
      taskExecution
    } = this.state;

    if (!taskExecution) {
      return <div>Loading ...</div>
    }

    const taskLink = (
      <Link to={path.TASKS + '/' + taskExecution.task.uuid}>
        {taskExecution.task.name}
      </Link>
    );

    return (
        <div className={styles.container}>
          <BreadcrumbBar
            firstLevel={taskLink}
            secondLevel={'Execution ' + taskExecution.uuid}
          />
          <Row>
            <Col>
              <TaskExecutionDetails taskExecution={taskExecution} />
            </Col>
          </Row>
        </div>
      );
  }
}

export default withRouter(TaskExecutionDetail);
