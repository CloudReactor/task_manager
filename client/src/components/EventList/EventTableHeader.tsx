import React from 'react';

interface Props {
  sortBy: string;
  descending: boolean;
  onSortChanged: (ordering?: string, toggleDirection?: boolean) => Promise<void>;
  showRunEnvironmentColumn?: boolean;
  showTaskWorkflowColumn?: boolean;
}

const EventTableHeader = (props: Props) => {
  const {
    sortBy,
    descending,
    onSortChanged,
    showRunEnvironmentColumn = true,
    showTaskWorkflowColumn = true
  } = props;

  const handleSortClick = (field: string) => {
    onSortChanged(field, true);
  };

  const renderSortIcon = (field: string) => {
    if (sortBy === field) {
      return (
        <span>
          &nbsp;
          <i className={'fas fa-arrow-' + (descending ? 'down' : 'up')} style={{ fontSize: '0.8em' }} />
        </span>
      );
    }
    return (
      <span style={{ opacity: 0.3 }}>
        &nbsp;
        <i className="fas fa-sort" style={{ fontSize: '0.8em' }} />
      </span>
    );
  };

  return (
    <thead>
      <tr>
        <th
          onClick={() => handleSortClick('event_at')}
          style={{ cursor: 'pointer' }}
        >
          Event Time{renderSortIcon('event_at')}
        </th>
        <th
          onClick={() => handleSortClick('severity')}
          style={{ cursor: 'pointer' }}
        >
          Severity{renderSortIcon('severity')}
        </th>
        <th
          onClick={() => handleSortClick('type')}
          style={{ cursor: 'pointer' }}
        >
          Event Type{renderSortIcon('type')}
        </th>
        <th>Summary</th>
        {showRunEnvironmentColumn && (
          <th
            onClick={() => handleSortClick('run_environment__name')}
            style={{ cursor: 'pointer' }}
          >
            Run Environment{renderSortIcon('run_environment__name')}
          </th>
        )}
        <th
          onClick={() => handleSortClick('detected_at')}
          style={{ cursor: 'pointer' }}
        >
          Detected At{renderSortIcon('detected_at')}
        </th>
        <th
          onClick={() => handleSortClick('acknowledged_at')}
          style={{ cursor: 'pointer' }}
        >
          Acknowledged{renderSortIcon('acknowledged_at')}
        </th>
        <th
          onClick={() => handleSortClick('resolved_at')}
          style={{ cursor: 'pointer' }}
        >
          Resolved{renderSortIcon('resolved_at')}
        </th>
        {showTaskWorkflowColumn && <th>Task/Workflow</th>}
        <th>Execution</th>
      </tr>
    </thead>
  );
};

export default EventTableHeader;
