import React from 'react';
import { Link } from 'react-router-dom';
import moment from 'moment';

import { AnyEvent } from '../../types/domain_types';
import { ResultsPage, itemsPerPageOptions } from '../../utils/api';

import DefaultPagination from '../Pagination/Pagination';

interface Props {
  eventPage: ResultsPage<AnyEvent>;
  currentPage: number;
  rowsPerPage: number;
  handlePageChanged: (currentPage: number) => void;
  handleSelectItemsPerPage: (event: React.ChangeEvent<HTMLSelectElement>) => void;
  showRunEnvironmentColumn?: boolean;
  showTaskWorkflowColumn?: boolean;
}

const EventTableBody = (props: Props) => {
  const {
    eventPage,
    currentPage,
    rowsPerPage,
    handlePageChanged,
    handleSelectItemsPerPage,
    showRunEnvironmentColumn = true,
    showTaskWorkflowColumn = true
  } = props;

  const formatTimestamp = (timestamp: Date | null) => {
    if (!timestamp) {
      return '-';
    }
    return moment(timestamp).format('YYYY-MM-DD HH:mm:ss');
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
            <Link to={`/events/${event.uuid}`}>
              {formatTimestamp(event.event_at)}
            </Link>
          </td>
          <td>
            <span className={getSeverityBadgeClass(event.severity)}>
              {event.severity.toUpperCase()}
            </span>
          </td>
          <td>{formatEventType(event.event_type)}</td>
          <td>{event.error_summary || '-'}</td>
          <td>{event.source || '-'}</td>
          {showRunEnvironmentColumn && <td>{event.run_environment?.name || '-'}</td>}
          <td>{formatTimestamp(event.detected_at)}</td>
          <td>{formatTimestamp(event.resolved_at)}</td>
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
      <tr>
        <td colSpan={10 - (showRunEnvironmentColumn ? 0 : 1) - (showTaskWorkflowColumn ? 0 : 1)}>
          <DefaultPagination
            currentPage={currentPage}
            pageSize={rowsPerPage}
            count={eventPage.count}
            handleClick={handlePageChanged}
            handleSelectItemsPerPage={handleSelectItemsPerPage}
            itemsPerPageOptions={itemsPerPageOptions}
          />
        </td>
      </tr>
    </tbody>
  );
};

export default EventTableBody;
