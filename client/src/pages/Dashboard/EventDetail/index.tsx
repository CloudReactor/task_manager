import * as path from '../../../constants/routes';

import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Row, Col } from 'react-bootstrap';

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
import { fetchEvent } from '../../../utils/api';
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

  const formatTs = (ts: Date | null | undefined) => ts ? moment(ts).format('YYYY-MM-DD HH:mm:ss') : '-';

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

  const titleCase = (input: string) => {
    if (!input) return input;
    // Preserve ALL-CAPS tokens like UUID
    if (!input.includes(' ') && input === input.toUpperCase()) return input;
    const smallWords = new Set([
      'a','an','the','and','but','or','for','nor','on','at','to','from','by','in','of','with','after','before','over','under','per','as','via'
    ]);
    const words = input.split(/\s+/).map(w => w.toLowerCase());
    return words.map((w, i) => {
      if (i === 0) return w.charAt(0).toUpperCase() + w.slice(1);
      if (smallWords.has(w)) return w;
      return w.charAt(0).toUpperCase() + w.slice(1);
    }).join(' ');
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
                <th>{titleCase('UUID')}</th>
                <td>{event.uuid}</td>
              </tr>
              <tr>
                <th>{titleCase('Event Time')}</th>
                <td>{formatTs(event.event_at)}</td>
              </tr>
              <tr>
                <th>{titleCase('Detected At')}</th>
                <td>{formatTs(event.detected_at)}</td>
              </tr>
              <tr>
                <th>{titleCase('Resolved At')}</th>
                <td>{formatTs(event.resolved_at)}</td>
              </tr>
              <tr>
                <th>{titleCase('Severity')}</th>
                <td>{event.severity}</td>
              </tr>
              <tr>
                <th>{titleCase('Event Type')}</th>
                <td>{formatEventType(event.event_type)}</td>
              </tr>
              <tr>
                <th>{titleCase('Summary')}</th>
                <td>{event.error_summary || '-'}</td>
              </tr>
              <tr>
                <th>{titleCase('Details')}</th>
                <td><pre style={{ whiteSpace: 'pre-wrap' }}>{event.details ? JSON.stringify(event.details, null, 2) : '-'}</pre></td>
              </tr>
              <tr>
                <th>{titleCase('Source')}</th>
                <td>{event.source || '-'}</td>
              </tr>
              <tr>
                <th>{titleCase('Grouping Key')}</th>
                <td>{event.grouping_key || '-'}</td>
              </tr>
              <tr>
                <th>{titleCase('Resolved Event')}</th>
                <td>{event.resolved_event ? <a href={event.resolved_event.url}>{event.resolved_event.uuid}</a> : '-'}</td>
              </tr>
              <tr>
                <th>{titleCase('Run Environment')}</th>
                <td>{event.run_environment ? <Link to={`/run_environments/${event.run_environment.uuid}`}>{event.run_environment.name}</Link> : '-'}</td>
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
                      <th>{titleCase('Status')}</th>
                      <td>{formatStatus((event as ExecutionStatusChangeEvent).status)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="triggered_at">
                      <th>{titleCase('Triggered At')}</th>
                      <td>{formatTs((event as ExecutionStatusChangeEvent).triggered_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="postponed_until">
                      <th>{titleCase('Postponed Until')}</th>
                      <td>{formatTs((event as ExecutionStatusChangeEvent).postponed_until)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="count_same_after">
                      <th>{titleCase('Count With Same Status After Postponement')}</th>
                      <td>{(event as ExecutionStatusChangeEvent).count_with_same_status_after_postponement ?? '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="count_success_after">
                      <th>{titleCase('Count With Success Status After Postponement')}</th>
                      <td>{(event as ExecutionStatusChangeEvent).count_with_success_status_after_postponement ?? '-'}</td>
                    </tr>
                  );
                }

                if (isTaskExecutionStatusChange(event)) {
                  // task and task_execution
                  rows.push(
                    <tr key="task">
                      <th>{titleCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="task_execution">
                      <th>{titleCase('Task Execution')}</th>
                      <td>{(event as any).task_execution ? <Link to={`/task_executions/${(event as any).task_execution.uuid}`}>{(event as any).task_execution.uuid}</Link> : '-'}</td>
                    </tr>
                  );
                }

                if (isWorkflowExecutionStatusChange(event)) {
                  rows.push(
                    <tr key="workflow">
                      <th>{titleCase('Workflow')}</th>
                      <td>{(event as any).workflow ? <Link to={`/workflows/${(event as any).workflow.uuid}`}>{(event as any).workflow.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="workflow_execution">
                      <th>{titleCase('Workflow Execution')}</th>
                      <td>{(event as any).workflow_execution ? <Link to={`/workflow_executions/${(event as any).workflow_execution.uuid}`}>{(event as any).workflow_execution.uuid}</Link> : '-'}</td>
                    </tr>
                  );
                }

                if (isMissingHeartbeat(event)) {
                  rows.push(
                    <tr key="mh_task">
                      <th>{titleCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="mh_task_execution">
                      <th>{titleCase('Task Execution')}</th>
                      <td>{(event as any).task_execution ? <Link to={`/task_executions/${(event as any).task_execution.uuid}`}>{(event as any).task_execution.uuid}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="last_heartbeat_at">
                      <th>{titleCase('Last Heartbeat At')}</th>
                      <td>{formatTs((event as MissingHeartbeatDetectionEvent).last_heartbeat_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="expected_heartbeat_at">
                      <th>{titleCase('Expected Heartbeat At')}</th>
                      <td>{formatTs((event as MissingHeartbeatDetectionEvent).expected_heartbeat_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="heartbeat_interval_seconds">
                      <th>{titleCase('Heartbeat Interval Seconds')}</th>
                      <td>{(event as MissingHeartbeatDetectionEvent).heartbeat_interval_seconds ?? '-'}</td>
                    </tr>
                  );
                }

                if (isInsufficientService(event)) {
                  rows.push(
                    <tr key="ist_task">
                      <th>{titleCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="interval_start_at">
                      <th>{titleCase('Interval Start At')}</th>
                      <td>{formatTs((event as InsufficientServiceTaskExecutionsEvent).interval_start_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="interval_end_at">
                      <th>{titleCase('Interval End At')}</th>
                      <td>{formatTs((event as InsufficientServiceTaskExecutionsEvent).interval_end_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="detected_concurrency">
                      <th>{titleCase('Detected Concurrency')}</th>
                      <td>{(event as InsufficientServiceTaskExecutionsEvent).detected_concurrency ?? '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="required_concurrency">
                      <th>{titleCase('Required Concurrency')}</th>
                      <td>{(event as InsufficientServiceTaskExecutionsEvent).required_concurrency ?? '-'}</td>
                    </tr>
                  );
                }

                if (isMissingScheduledTask(event)) {
                  rows.push(
                    <tr key="mst_task">
                      <th>{titleCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="mst_schedule">
                      <th>{titleCase('Schedule')}</th>
                      <td>{(event as MissingScheduledTaskExecutionEvent).schedule ?? '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="mst_expected_execution_at">
                      <th>{titleCase('Expected Execution At')}</th>
                      <td>{formatTs((event as MissingScheduledTaskExecutionEvent).expected_execution_at)}</td>
                    </tr>
                  );
                }

                if (isMissingScheduledWorkflow(event)) {
                  rows.push(
                    <tr key="msw_workflow">
                      <th>{titleCase('Workflow')}</th>
                      <td>{(event as any).workflow ? <Link to={`/workflows/${(event as any).workflow.uuid}`}>{(event as any).workflow.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="msw_schedule">
                      <th>{titleCase('Schedule')}</th>
                      <td>{(event as MissingScheduledWorkflowExecutionEvent).schedule ?? '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="msw_expected_execution_at">
                      <th>{titleCase('Expected Execution At')}</th>
                      <td>{formatTs((event as MissingScheduledWorkflowExecutionEvent).expected_execution_at)}</td>
                    </tr>
                  );
                }

                if (isDelayedTaskExecutionStart(event)) {
                  rows.push(
                    <tr key="dtes_task">
                      <th>{titleCase('Task')}</th>
                      <td>{(event as any).task ? <Link to={`/tasks/${(event as any).task.uuid}`}>{(event as any).task.name}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="dtes_task_execution">
                      <th>{titleCase('Task Execution')}</th>
                      <td>{(event as any).task_execution ? <Link to={`/task_executions/${(event as any).task_execution.uuid}`}>{(event as any).task_execution.uuid}</Link> : '-'}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="dtes_desired_start_at">
                      <th>{titleCase('Desired Start At')}</th>
                      <td>{formatTs((event as DelayedTaskExecutionStartEvent).desired_start_at)}</td>
                    </tr>
                  );

                  rows.push(
                    <tr key="dtes_expected_start_by_deadline">
                      <th>{titleCase('Expected Start By Deadline')}</th>
                      <td>{formatTs((event as DelayedTaskExecutionStartEvent).expected_start_by_deadline)}</td>
                    </tr>
                  );
                }

                return rows;
              })()}
              <tr>
                <th>{titleCase('Created At')}</th>
                <td>{formatTs(event.created_at)}</td>
              </tr>
              <tr>
                <th>{titleCase('Updated At')}</th>
                <td>{formatTs(event.updated_at)}</td>
              </tr>
            </tbody>
          </table>
        </Col>
      </Row>
    </div>
  );
};

export default abortableHoc(EventDetail);
