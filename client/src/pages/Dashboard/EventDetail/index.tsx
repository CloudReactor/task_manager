import * as path from '../../../constants/routes';

import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Row, Col } from 'react-bootstrap';
import { startCase } from 'lodash-es';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCheckCircle, faEye } from '@fortawesome/free-solid-svg-icons'

import { AnyEvent,
  ExecutionStatusChangeEvent,
  TaskExecutionStatusChangeEvent,
  WorkflowExecutionStatusChangeEvent,
  MissingHeartbeatDetectionEvent,
  InsufficientServiceTaskExecutionsEvent,
  MissingScheduledTaskExecutionEvent,
  MissingScheduledWorkflowExecutionEvent,
  DelayedTaskExecutionStartEvent
} from '../../../types/domain_types';
import { fetchEvent, updateEvent } from '../../../utils/api';
import { getSeverityBadgeClass } from '../../../utils/ui_utils';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';
import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import Loading from '../../../components/Loading';
import moment from 'moment';

import styles from './index.module.scss';

type PathParamsType = {
  uuid: string;
};

type Props = AbortSignalProps;

const EventDetail = ({ abortSignal }: Props) => {
  const { uuid } = useParams<PathParamsType>();

  const [isLoading, setLoading] = useState(false);
  const [event, setEvent] = useState<AnyEvent | null>(null);
  const [acknowledgeLoading, setAcknowledgeLoading] = useState(false);
  const [resolveLoading, setResolveLoading] = useState(false);

  const loadEvent = useCallback(async () => {
    if (!uuid) return;
    setLoading(true);
    try {
      const fetched = await fetchEvent(uuid, abortSignal);
      setEvent(fetched);
    } catch (e) {
      console.error('Failed to load event', e);
    } finally {
      setLoading(false);
    }
  }, [uuid]);

  useEffect(() => {
    document.title = 'Event Details';
    if (!event && !isLoading) {
      loadEvent();
    }
  }, [event, isLoading]);

  if (!event) {
    return <Loading />;
  }

  const formatTs = (ts: Date | null | undefined) => ts ? moment.utc(ts).format('YYYY-MM-DD HH:mm:ss') : '-';

  const formatEventType = (eventType: string) => {
    if (!eventType) return '-';
    // remove trailing '_event' or 'event' (case-insensitive), then convert snake_case to Title Case
    const withoutSuffix = eventType.replace(/_?event$/i, '');
    return withoutSuffix
      .split(/[_\s]+/)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const formatStatus = (status?: string | number | null) => {
    if (status === undefined || status === null) return '-';
    const s = String(status);
    const words = s.replace(/[_-]+/g, ' ').trim().toLowerCase().split(/\s+/);
    if (words.length === 0) return '-';
    words[0] = words[0].charAt(0).toUpperCase() + words[0].slice(1);
    return words.join(' ');
  };

  const handleAcknowledgeEvent = async () => {
    if (!event) return;
    setAcknowledgeLoading(true);
    try {
      await updateEvent(event.uuid, {
        acknowledged_at: moment.utc().toISOString()
      });
      setEvent({
        ...event,
        acknowledged_at: new Date(),
        acknowledged_by_user: 'You'
      });
    } catch (error) {
      console.error('Failed to acknowledge event:', error);
    } finally {
      setAcknowledgeLoading(false);
    }
  };

  const handleResolveEvent = async () => {
    if (!event) return;
    setResolveLoading(true);
    try {
      await updateEvent(event.uuid, {
        resolved_at: moment.utc().toISOString()
      });
      setEvent({
        ...event,
        resolved_at: new Date(),
        resolved_by_user: 'You'
      });
    } catch (error) {
      console.error('Failed to resolve event:', error);
    } finally {
      setResolveLoading(false);
    }
  };

  const firstLevel = (
    <Link to={path.EVENTS}>Events</Link>
  );

  return (
    <div className={styles.container}>
      <BreadcrumbBar
        firstLevel={firstLevel}
        secondLevel={`Event ${event.uuid}`}
      />
      <Row>
        <Col>
          <table className="table table-striped">
            <tbody>
              <tr>
                <th>{startCase('UUID')}</th>
                <td>{event.uuid}</td>
              </tr>
              <tr>
                <th>{startCase('Run Environment')}</th>
                <td>{event.run_environment ? <Link to={`/run_environments/${event.run_environment.uuid}`}>{event.run_environment.name}</Link> : '-'}</td>
              </tr>
              <tr>
                <th>{startCase('Severity')}</th>
                <td>
                  <span className={getSeverityBadgeClass(event.severity)}>
                    {event.severity.toUpperCase()}
                  </span>
                </td>
              </tr>
              <tr>
                <th>{startCase('Event Time')}</th>
                <td>{formatTs(event.event_at)}</td>
              </tr>
              <tr>
                <th>{startCase('Detected At')}</th>
                <td>{formatTs(event.detected_at)}</td>
              </tr>
              <tr>
                <th>Acknowledgement</th>
                <td>
                  {event.acknowledged_at ? (
                    <>
                      {formatTs(event.acknowledged_at)}
                      {event.acknowledged_by_user && (
                        <span> by {event.acknowledged_by_user}</span>
                      )}
                    </>
                  ) : (
                    <button
                      className="btn btn-sm btn-secondary d-inline-flex align-items-center"
                      onClick={handleAcknowledgeEvent}
                      disabled={acknowledgeLoading}
                      style={{ width: '130px' }}
                    >
                      <span style={{ marginRight: '0.5rem' }}><FontAwesomeIcon icon={faEye} /></span>
                      <span style={{ whiteSpace: 'nowrap' }}>{acknowledgeLoading ? 'Acknowledging...' : 'Acknowledge'}</span>
                    </button>
                  )}
                </td>
              </tr>
              <tr>
                <th>Resolution</th>
                <td>
                  {event.resolved_at ? (
                    <>
                      {formatTs(event.resolved_at)}
                      {event.resolved_by_user && (
                        <span> by {event.resolved_by_user}</span>
                      )}
                    </>
                  ) : (
                    <button
                      className="btn btn-sm btn-secondary d-inline-flex align-items-center"
                      onClick={handleResolveEvent}
                      disabled={resolveLoading}
                      style={{ width: '130px' }}
                    >
                      <span style={{ marginRight: '0.5rem' }}><FontAwesomeIcon icon={faCheckCircle} /></span>
                      <span style={{ whiteSpace: 'nowrap' }}>{resolveLoading ? 'Resolving...' : 'Resolve'}</span>
                    </button>
                  )}
                </td>
              </tr>
              <tr>
                <th>{startCase('Event Type')}</th>
                <td>{formatEventType(event.event_type)}</td>
              </tr>
              <tr>
                <th>{startCase('Summary')}</th>
                <td>{event.error_summary || '-'}</td>
              </tr>
              <tr>
                <th>{startCase('Details')}</th>
                <td><pre style={{ whiteSpace: 'pre-wrap' }}>{event.details ? JSON.stringify(event.details, null, 2) : '-'}</pre></td>
              </tr>
              <tr>
                <th>{startCase('Source')}</th>
                <td>{event.source || '-'}</td>
              </tr>
              <tr>
                <th>{startCase('Grouping Key')}</th>
                <td>{event.grouping_key || '-'}</td>
              </tr>
              <tr>
                <th>{startCase('Resolved Event')}</th>
                <td>{event.resolved_event ? <a href={event.resolved_event.url}>{event.resolved_event.uuid}</a> : '-'}</td>
              </tr>
              <tr>
                <th>{startCase('Created At')}</th>
                <td>{formatTs(event.created_at)}</td>
              </tr>
              <tr>
                <th>{startCase('Updated At')}</th>
                <td>{formatTs(event.updated_at)}</td>
              </tr>
              {/* Subclass-specific fields */}
              {(() => {
                const rows: JSX.Element[] = [];

                const isExecutionStatusChange = (e: AnyEvent): e is ExecutionStatusChangeEvent => {
                  return (e as any).status !== undefined || (e as any).postponed_until !== undefined || (e as any).triggered_at !== undefined;
                };

                const isTaskExecutionStatusChange = (e: AnyEvent): e is TaskExecutionStatusChangeEvent => {
                  return isExecutionStatusChange(e) && !!(e as any).task_execution;
                };

                const isWorkflowExecutionStatusChange = (e: AnyEvent): e is WorkflowExecutionStatusChangeEvent => {
                  return isExecutionStatusChange(e) && !!(e as any).workflow_execution;
                };

                const isMissingHeartbeat = (e: AnyEvent): e is MissingHeartbeatDetectionEvent => {
                  return (e as any).last_heartbeat_at !== undefined || (e as any).expected_heartbeat_at !== undefined;
                };

                const isInsufficientService = (e: AnyEvent): e is InsufficientServiceTaskExecutionsEvent => {
                  return (e as any).detected_concurrency !== undefined || (e as any).required_concurrency !== undefined;
                };

                const isMissingScheduledTask = (e: AnyEvent): e is MissingScheduledTaskExecutionEvent => {
                  return (e as any).schedule !== undefined && !!(e as any).task;
                };

                const isMissingScheduledWorkflow = (e: AnyEvent): e is MissingScheduledWorkflowExecutionEvent => {
                  return (e as any).schedule !== undefined && !!(e as any).workflow;
                };

                const isDelayedTaskExecutionStart = (e: AnyEvent): e is DelayedTaskExecutionStartEvent => {
                  return (e as any).desired_start_at !== undefined || (e as any).expected_start_by_deadline !== undefined;
                };

                // Execution status change (task/workflow shared fields)
                if (isExecutionStatusChange(event)) {
                  rows.push(
                    <tr key="status">
                      <th>{startCase('Status')}</th>
                      <td>{formatStatus((event as ExecutionStatusChangeEvent).status)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="triggered_at">
                      <th>{startCase('Triggered At')}</th>
                      <td>{formatTs((event as ExecutionStatusChangeEvent).triggered_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="postponed_until">
                      <th>{startCase('Postponed Until')}</th>
                      <td>{formatTs((event as ExecutionStatusChangeEvent).postponed_until)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="count_same_after">
                      <th>{startCase('Count With Same Status After Postponement')}</th>
                      <td>{(event as ExecutionStatusChangeEvent).count_with_same_status_after_postponement ?? '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="count_success_after">
                      <th>{startCase('Count With Success Status After Postponement')}</th>
                      <td>{(event as ExecutionStatusChangeEvent).count_with_success_status_after_postponement ?? '-'}</td>
                    </tr>
                  );
                }

                if (isTaskExecutionStatusChange(event)) {
                  // task and task_execution
                  rows.push(
                    <tr key="task">
                      <th>{startCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="task_execution">
                      <th>{startCase('Task Execution')}</th>
                      <td>{(event as any).task_execution ? <Link to={`/task_executions/${(event as any).task_execution.uuid}`}>{(event as any).task_execution.uuid}</Link> : '-'}</td>
                    </tr>
                  );
                }

                if (isWorkflowExecutionStatusChange(event)) {
                  rows.push(
                    <tr key="workflow">
                      <th>{startCase('Workflow')}</th>
                      <td>{(event as any).workflow ? <Link to={`/workflows/${(event as any).workflow.uuid}`}>{(event as any).workflow.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="workflow_execution">
                      <th>{startCase('Workflow Execution')}</th>
                      <td>{(event as any).workflow_execution ? <Link to={`/workflow_executions/${(event as any).workflow_execution.uuid}`}>{(event as any).workflow_execution.uuid}</Link> : '-'}</td>
                    </tr>
                  );
                }

                if (isMissingHeartbeat(event)) {
                  rows.push(
                    <tr key="mh_task">
                      <th>{startCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="mh_task_execution">
                      <th>{startCase('Task Execution')}</th>
                      <td>{(event as any).task_execution ? <Link to={`/task_executions/${(event as any).task_execution.uuid}`}>{(event as any).task_execution.uuid}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="last_heartbeat_at">
                      <th>{startCase('Last Heartbeat At')}</th>
                      <td>{formatTs((event as MissingHeartbeatDetectionEvent).last_heartbeat_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="expected_heartbeat_at">
                      <th>{startCase('Expected Heartbeat At')}</th>
                      <td>{formatTs((event as MissingHeartbeatDetectionEvent).expected_heartbeat_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="heartbeat_interval_seconds">
                      <th>{startCase('Heartbeat Interval Seconds')}</th>
                      <td>{(event as MissingHeartbeatDetectionEvent).heartbeat_interval_seconds ?? '-'}</td>
                    </tr>
                  );
                }

                if (isInsufficientService(event)) {
                  rows.push(
                    <tr key="ist_task">
                      <th>{startCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="interval_start_at">
                      <th>{startCase('Interval Start At')}</th>
                      <td>{formatTs((event as InsufficientServiceTaskExecutionsEvent).interval_start_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="interval_end_at">
                      <th>{startCase('Interval End At')}</th>
                      <td>{formatTs((event as InsufficientServiceTaskExecutionsEvent).interval_end_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="detected_concurrency">
                      <th>{startCase('Detected Concurrency')}</th>
                      <td>{(event as InsufficientServiceTaskExecutionsEvent).detected_concurrency ?? '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="required_concurrency">
                      <th>{startCase('Required Concurrency')}</th>
                      <td>{(event as InsufficientServiceTaskExecutionsEvent).required_concurrency ?? '-'}</td>
                    </tr>
                  );
                }

                if (isMissingScheduledTask(event)) {
                  rows.push(
                    <tr key="mst_task">
                      <th>{startCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="mst_schedule">
                      <th>{startCase('Schedule')}</th>
                      <td>{(event as MissingScheduledTaskExecutionEvent).schedule ?? '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="mst_expected_execution_at">
                      <th>{startCase('Expected Execution At')}</th>
                      <td>{formatTs((event as MissingScheduledTaskExecutionEvent).expected_execution_at)}</td>
                    </tr>
                  );
                }

                if (isMissingScheduledWorkflow(event)) {
                  rows.push(
                    <tr key="msw_workflow">
                      <th>{startCase('Workflow')}</th>
                      <td>{(event as any).workflow ? <Link to={`/workflows/${(event as any).workflow.uuid}`}>{(event as any).workflow.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="msw_schedule">
                      <th>{startCase('Schedule')}</th>
                      <td>{(event as MissingScheduledWorkflowExecutionEvent).schedule ?? '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="msw_expected_execution_at">
                      <th>{startCase('Expected Execution At')}</th>
                      <td>{formatTs((event as MissingScheduledWorkflowExecutionEvent).expected_execution_at)}</td>
                    </tr>
                  );
                }

                if (isDelayedTaskExecutionStart(event)) {
                  rows.push(
                    <tr key="dtes_task">
                      <th>{startCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="dtes_task_execution">
                      <th>{startCase('Task Execution')}</th>
                      <td>{(event as any).task_execution ? <Link to={`/task_executions/${(event as any).task_execution.uuid}`}>{(event as any).task_execution.uuid}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="dtes_desired_start_at">
                      <th>{startCase('Desired Start At')}</th>
                      <td>{formatTs((event as DelayedTaskExecutionStartEvent).desired_start_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="dtes_expected_start_by_deadline">
                      <th>{startCase('Expected Start By Deadline')}</th>
                      <td>{formatTs((event as DelayedTaskExecutionStartEvent).expected_start_by_deadline)}</td>
                    </tr>
                  );
                }

                return rows;
              })()}
            </tbody>
          </table>
        </Col>
      </Row>
    </div>
  );
};

export default abortableHoc(EventDetail);
