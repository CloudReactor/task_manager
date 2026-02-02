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
      return descending ? ' ▼' : ' ▲';
    }
    return '';
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
        <th>Event Type</th>
        <th>Summary</th>
        {showRunEnvironmentColumn && <th>Run Environment</th>}
        <th
          onClick={() => handleSortClick('detected_at')}
          style={{ cursor: 'pointer' }}
        >
          Detected At{renderSortIcon('detected_at')}
        </th>
        <th
          onClick={() => handleSortClick('resolved_at')}
          style={{ cursor: 'pointer' }}
        >
          Resolved At{renderSortIcon('resolved_at')}
        </th>
        {showTaskWorkflowColumn && <th>Task/Workflow</th>}
        <th>Execution</th>
      </tr>
    </thead>
  );
};

export default EventTableHeader;
