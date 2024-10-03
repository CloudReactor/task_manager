import _ from 'lodash';

import * as path from '../../constants/routes';

import {
  WorkflowTaskInstance,
  WorkflowTaskInstanceExecution,
} from "../../types/domain_types";

import React, { Component, Fragment }  from 'react';

import { Link } from 'react-router-dom'

import {
  Row,
  Col
} from 'react-bootstrap'

import Status from '../Status/Status';
import {timeDuration, timeFormat} from '../../utils';
import ActionButton from '../common/ActionButton';

interface Props {
  workflowTaskInstance: WorkflowTaskInstance,
  // should be ordered from most recently started to least recently started
  executions: WorkflowTaskInstanceExecution[],
  onStartRequested: (workflowTaskInstance: WorkflowTaskInstance) => void
}

interface State {
  isStartInProgress: boolean
}

export default class WorkflowTaskInstancePanel extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    this.state = {
      isStartInProgress: false
    };
  }

  public render() {
    const {
      workflowTaskInstance,
      executions
    } = this.props;

    const {
      isStartInProgress
    } = this.state;

    const wti = workflowTaskInstance;
    const task = wti.task ?? wti.process_type;

    if (!task) {
      return <div>Missing task!</div>;
    }

    const latestExecution = (executions.length > 0) ? executions[0] : null;
    const latestTaskExecution = latestExecution ? latestExecution.task_execution : null;

    return (
      (<Fragment>
        <Row>
          <Col>
             <h4>{wti.name}</h4>
          </Col>
        </Row>
        <Row>
          <Col>
             <ActionButton onActionRequested={this.handleActionRequested}
              cbData={wti} action="start" label={ latestExecution ? 'Restart' : 'Start' }
              faIconName="play"
              inProgress={isStartInProgress}
              inProgressLabel={ latestExecution ? 'Restarting ...' : 'Start ...' } />
          </Col>
        </Row>
        <Row>
          <Col>
            <dl>
              <dt>Task</dt>
              <dd><Link to={path.TASKS + '/' + encodeURIComponent(task.uuid)}>{task.name}</Link></dd>
            </dl>

            <dl>
              <dt>Required transitions to start</dt>
              <dd>
                { _.capitalize(wti.start_transition_condition.replace(/_/g, ' ')) }
              </dd>
            </dl>
            <dl>
              <dt>Failure behavior</dt>
              <dd>
                { _(wti.failure_behavior.replace(/_/g, ' ')).capitalize() }
              </dd>
            </dl>
            <dl>
              <dt>Continue Workflow execution after failure</dt>
              <dd>
                { wti.allow_workflow_execution_after_failure ? 'Yes' : 'No' }
              </dd>
            </dl>
            <dl>
              <dt>Timeout behavior</dt>
              <dd>
                { _.capitalize(wti.timeout_behavior.replace(/_/g, ' ')) }
              </dd>
            </dl>
            <dl>
              <dt>Continue Workflow execution after timeout</dt>
              <dd>
                { wti.allow_workflow_execution_after_timeout ? 'Yes' : 'No' }
              </dd>
            </dl>
            <dl>
              <dt>Latest execution status</dt>
              <dd>
                {
                  latestTaskExecution ?
                  (
                    <span>
                      <Status enabled={true} status={latestTaskExecution.status}
                       isService={false} forExecutionDetail={true} />
                      &nbsp;
                      <Link to={path.TASK_EXECUTIONS + '/' + encodeURIComponent(latestTaskExecution.uuid)}>Details ...</Link>
                    </span>
                  ) : 'Never executed'
                }
              </dd>

              {
                latestTaskExecution && (
                  <Fragment>
                    {
                      latestTaskExecution.task_version_signature && (
                        <Fragment>
                          <dt>Commit</dt>
                          <dd>
                            {
                              latestTaskExecution.commit_url ?
                              <a href={latestTaskExecution.commit_url} target={latestTaskExecution.commit_url}>
                                {latestTaskExecution.task_version_signature}
                              </a> :
                              <span>{latestTaskExecution.task_version_signature}</span>
                            }
                          </dd>
                        </Fragment>
                      )
                    }
                    <dt>Started at</dt>
                    <dd>{ timeFormat(latestTaskExecution.started_at, true) }</dd>
                    <dt>Finished at</dt>
                    <dd>
                      {
                        latestTaskExecution.finished_at ?
                        timeFormat(latestTaskExecution.finished_at, true) :
                        'N/A'
                      }
                    </dd>
                    <dt>Duration</dt>
                    <dd>
                      {
                        timeDuration(latestTaskExecution.started_at, latestTaskExecution.finished_at)
                      }
                    </dd>
                    <dt>Last heartbeat at</dt>
                    <dd>
                      {
                        latestTaskExecution.last_heartbeat_at ?
                        timeFormat(latestTaskExecution.last_heartbeat_at, true) :
                        'N/A'
                      }
                    </dd>
                    <dt>Exit code</dt>
                    <dd>
                      {
                        (latestTaskExecution.exit_code === 0) ? '0' :
                        (latestTaskExecution.exit_code || 'N/A')
                      }
                    </dd>
                    <dt>Failed attempts</dt>
                    <dd>{latestTaskExecution.failed_attempts}</dd>
                    <dt>Timed out attempts</dt>
                    <dd>{latestTaskExecution.timed_out_attempts}</dd>
                  </Fragment>
                )
              }

            </dl>
          </Col>
        </Row>
      </Fragment>)
    );
  }

  handleActionRequested = async (action: string | undefined, cbData: any) => {
    switch (action) {
      case 'start':
        this.setState({
          isStartInProgress: true
        });
        try {
          await this.props.onStartRequested(cbData as WorkflowTaskInstance);

          this.setState({
            isStartInProgress: false
          });
        } catch (err) {
          this.setState({
            isStartInProgress: false
          });
        }
        break;

      default:
        throw new Error(`Unknown action: '${action}'`);
    }
  }
}