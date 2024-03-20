import * as path from '../../../constants/routes';

import { RunEnvironment, Task, TaskExecution } from '../../../types/domain_types';

import * as UIC from '../../../utils/ui_constants';
import { fetchRunEnvironment, fetchTask, fetchTaskExecution } from '../../../utils/api';

import React, {  useEffect, useState } from "react";
import { Link, useParams } from 'react-router-dom'

import { Row, Col } from 'react-bootstrap';

import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';
import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import Loading from '../../../components/Loading';
import TaskExecutionDetails from "../../../components/TaskExecutionDetails/TaskExecutionDetails";

import styles from './index.module.scss';
import {TASK_EXECUTION_STATUSES_IN_PROGRESS} from '../../../utils/constants';

type PathParamsType = {
  uuid: string;
};

type Props = AbortSignalProps;

const TaskExecutionDetail = ({
  abortSignal
}: Props) => {
  const {
    uuid
  } = useParams<PathParamsType>();

  if (!uuid) {
    return <div>Invalid UUID</div>;
  }

  const [taskExecution, setTaskExecution] = useState<TaskExecution | null>(null);
  const [task, setTask] = useState<Task | null>(null);
  const [runEnvironment, setRunEnvironment] = useState<RunEnvironment | null>(null);
  const [selfInterval, setSelfInterval] = useState<any>(null);

  const fetchExecutionDetails = async () => {
    try {
      const fetchedExecution = await fetchTaskExecution(uuid, abortSignal);

      setTaskExecution(fetchedExecution);

      if (!task) {
        const fetchedTask = await fetchTask(fetchedExecution.task.uuid, abortSignal);
        setTask(fetchedTask);

        if (!runEnvironment) {
          const fetchedRunEnvironment = await fetchRunEnvironment(fetchedTask.run_environment.uuid, abortSignal);
          setRunEnvironment(fetchedRunEnvironment);
        }
      }

      if (TASK_EXECUTION_STATUSES_IN_PROGRESS.includes(fetchedExecution.status)) {
        if (!selfInterval) {
          const interval = setInterval(fetchExecutionDetails,
            UIC.TASK_REFRESH_INTERVAL_MILLIS);
          setSelfInterval(interval);
        }
      } else {
        if (selfInterval) {
          clearInterval(selfInterval);
          setSelfInterval(null);
        }
      }
    } catch (error) {
      console.log(error);
    }
  };

  useEffect(() => {
    document.title = 'Task Execution Details';
    if (!taskExecution) {
      fetchExecutionDetails();
    }
  }, [taskExecution]);

  useEffect(() => {
    return () => {
      if (selfInterval) {
        clearInterval(selfInterval);
      }
    };
  }, []);

  if (!taskExecution) {
    return <Loading />
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
          <TaskExecutionDetails taskExecution={taskExecution} task={task}
           runEnvironment={runEnvironment} />
        </Col>
      </Row>
    </div>
  );
}

export default abortableHoc(TaskExecutionDetail);
