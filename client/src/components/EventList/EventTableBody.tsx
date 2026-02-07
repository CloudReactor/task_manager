import React, { useContext, useState } from 'react';
import { Link } from 'react-router-dom';

import { faCheckCircle, faEye } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

import moment from 'moment';

import { GlobalContext, accessLevelForCurrentGroup } from '../../context/GlobalContext';
import { AnyEvent } from '../../types/domain_types';
import { ResultsPage, updateEvent } from '../../utils/api';
import { ACCESS_LEVEL_SUPPORT } from '../../utils/constants';
import styles from './EventTableBody.module.scss';



interface Props {
  eventPage: ResultsPage<AnyEvent>;
  currentPage: number;
  rowsPerPage: number;
  handlePageChanged: (currentPage: number) => void;
  handleSelectItemsPerPage: (event: React.ChangeEvent<HTMLSelectElement>) => void;
  showRunEnvironmentColumn?: boolean;
  showTaskWorkflowColumn?: boolean;
  onEventAcknowledged?: (eventUuid: string) => void;
}

const EventTableBody = (props: Props) => {
  const {
    eventPage,
    currentPage,
    rowsPerPage,
    handlePageChanged,
    handleSelectItemsPerPage,
    showRunEnvironmentColumn = true,
    showTaskWorkflowColumn = true,
    onEventAcknowledged
  } = props;

  const globalContext = useContext(GlobalContext);
  const userAccessLevel = accessLevelForCurrentGroup(globalContext);

  const [acknowledgeLoadingMap, setAcknowledgeLoadingMap] = useState<{ [uuid: string]: boolean }>({});
  const [resolveLoadingMap, setResolveLoadingMap] = useState<{ [uuid: string]: boolean }>({});

  const handleAcknowledgeEvent = async (eventUuid: string) => {
    setAcknowledgeLoadingMap(prev => ({ ...prev, [eventUuid]: true }));
    try {
      await updateEvent(eventUuid, {
        acknowledged_at: moment.utc().toISOString()
      });
      if (onEventAcknowledged) {
        onEventAcknowledged(eventUuid);
      }
    } catch (error) {
      console.error('Failed to acknowledge event:', error);
    } finally {
      setAcknowledgeLoadingMap(prev => ({ ...prev, [eventUuid]: false }));
    }
  };

  const handleResolveEvent = async (eventUuid: string) => {
    setResolveLoadingMap(prev => ({ ...prev, [eventUuid]: true }));
    try {
      await updateEvent(eventUuid, {
        resolved_at: moment.utc().toISOString()
      });
      if (onEventAcknowledged) {
        onEventAcknowledged(eventUuid);
      }
    } catch (error) {
      console.error('Failed to resolve event:', error);
    } finally {
      setResolveLoadingMap(prev => ({ ...prev, [eventUuid]: false }));
    }
  };

  const canAcknowledge = userAccessLevel !== null && userAccessLevel !== undefined && userAccessLevel >= ACCESS_LEVEL_SUPPORT;
  const canResolve = canAcknowledge;

  const formatTimestamp = (timestamp: Date | null) => {
    if (!timestamp) {
      return '-';
    }
    // show time in UTC (no timezone suffix)
    return moment.utc(timestamp).format('YYYY-MM-DD HH:mm:ss');
  };

  const formatAgo = (timestamp: Date | null) => {
    if (!timestamp) return '';
    // compute relative time using UTC
    return moment.utc(timestamp).fromNow();
  };

  const formatEventType = (eventType: string) => {
    // Convert snake_case to Title Case and remove '_event' suffix
    const withoutSuffix = eventType.replace(/_event$/, '');
    return withoutSuffix
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const renderTaskOrWorkflow = (event: AnyEvent) => {
    const eAny = event as any;
    if (eAny.task) {
      return (
        <Link to={`/tasks/${eAny.task.uuid}`}>
          {eAny.task.name}
        </Link>
      );
    }
    if (eAny.workflow) {
      return (
        <Link to={`/workflows/${eAny.workflow.uuid}`}>
          {eAny.workflow.name}
        </Link>
      );
    }
    return '-';
  };

  const renderExecution = (event: AnyEvent) => {
    const eAny = event as any;
    if (eAny.task_execution) {
      return (
        <Link to={`/task_executions/${eAny.task_execution.uuid}`}>
          {eAny.task_execution.uuid}
        </Link>
      );
    }
    if (eAny.workflow_execution) {
      return (
        <Link to={`/workflow_executions/${eAny.workflow_execution.uuid}`}>
          {eAny.workflow_execution.uuid}
        </Link>
      );
    }
    return '-';
  };

  const renderRunEnvironment = (event: AnyEvent) => {
    if (event.run_environment) {
      return (
        <Link to={`/run_environments/${event.run_environment.uuid}`}>
          {event.run_environment.name}
        </Link>
      );
    }
    return '-';
  };

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'badge badge-danger';
      case 'error':
        return 'badge badge-danger';
      case 'warning':
        return 'badge badge-warning';
      case 'info':
        return 'badge badge-info';
      case 'debug':
        return 'badge badge-secondary';
      case 'trace':
        return 'badge badge-light';
      default:
        return 'badge badge-secondary';
    }
  };

  return (
    <tbody>
      {eventPage.results.map((event: AnyEvent) => (
        <tr key={event.uuid}>
          <td>
            <Link to={`/events/${event.uuid}`} className={styles.eventLink}>
              {formatTimestamp(event.event_at)}
              {event.event_at && (
                <span className="text-muted"> ({formatAgo(event.event_at)})</span>
              )}
            </Link>
          </td>
          <td>
            <span className={getSeverityBadgeClass(event.severity)}>
              {event.severity.toUpperCase()}
            </span>
          </td>
          <td>{formatEventType(event.event_type)}</td>
          <td>
            {event.error_summary ? (
              <Link to={`/events/${event.uuid}`} className={styles.eventLink}>
                {event.error_summary}
              </Link>
            ) : (
              '-'
            )}
          </td>
          {showRunEnvironmentColumn && <td>{renderRunEnvironment(event)}</td>}
          <td>
            {formatTimestamp(event.detected_at)}
            {event.detected_at && (
              <span className="text-muted"> ({formatAgo(event.detected_at)})</span>
            )}
          </td>
          <td>
            {event.acknowledged_at ? (
              <>
                {formatTimestamp(event.acknowledged_at)}
                <span className="text-muted"> ({formatAgo(event.acknowledged_at)})</span>
                {event.acknowledged_by_user && (
                    <span> by {event.acknowledged_by_user}</span>
                )}
              </>
            ) : (
              (canAcknowledge ? (
                <button
                  className="btn btn-sm btn-secondary d-inline-flex align-items-center"
                  onClick={() => handleAcknowledgeEvent(event.uuid)}
                  disabled={acknowledgeLoadingMap[event.uuid] || false}
                >
                  <span style={{ marginRight: '0.5rem' }}><FontAwesomeIcon icon={faEye} /></span>
                  <span style={{ whiteSpace: 'nowrap' }}>{acknowledgeLoadingMap[event.uuid] ? 'Acknowledging...' : 'Acknowledge'}</span>
                </button>
              ) : '-')
            )}
          </td>
          <td>
            {event.resolved_at ? (
              <>
                {formatTimestamp(event.resolved_at)}
                <span className="text-muted"> ({formatAgo(event.resolved_at)})</span>
                {event.resolved_by_user && (
                    <span> by {event.resolved_by_user}</span>
                )}
              </>
            ) : (
              (canResolve ? (
                <button
                  className="btn btn-sm btn-secondary d-inline-flex align-items-center"
                  onClick={() => handleResolveEvent(event.uuid)}
                  disabled={resolveLoadingMap[event.uuid] || false}
                >
                  <span style={{ marginRight: '0.5rem' }}><FontAwesomeIcon icon={faCheckCircle} /></span>
                  <span style={{ whiteSpace: 'nowrap' }}>{resolveLoadingMap[event.uuid] ? 'Resolving...' : 'Resolve'}</span>
                </button>
              ) : '-')
            )}
          </td>
          {showTaskWorkflowColumn && <td>{renderTaskOrWorkflow(event)}</td>}
          <td>{renderExecution(event)}</td>
        </tr>
      ))}

      {eventPage.results.length === 0 && (
        <tr>
          <td colSpan={10 - (showRunEnvironmentColumn ? 0 : 1) - (showTaskWorkflowColumn ? 0 : 1)} className="text-center">
            No events found
          </td>
        </tr>
      )}
    </tbody>
  );
};

export default EventTableBody;
