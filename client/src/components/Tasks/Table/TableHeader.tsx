import React from 'react';
import { TableColumnInfo } from "../../../types/ui_types";
import "../style.scss";
import "../../../styles/tableStyles.scss";

const TASK_COLUMNS: TableColumnInfo[] = [
  { name: 'Name', ordering: 'name' },
  { name: 'Enabled', ordering: 'enabled', textAlign: 'text-center' },
  { name: 'Type', ordering: 'execution_time_kind' },
  { name: 'Status', ordering: 'latest_task_execution__status' },
  { name: 'Started', ordering: 'latest_task_execution__started_at' },
  { name: 'Finished', ordering: 'latest_task_execution__finished_at' },
  { name: 'Duration', ordering: 'latest_task_execution__duration' },
  { name: 'Last heartbeat', ordering: 'latest_task_execution__last_heartbeat_at' },
  {
    name: 'Processed',
    ordering: 'latest_task_execution__success_count',
    textAlign: 'text-right'
  },
  { name: 'Schedule', ordering: 'schedule' },
  { name: 'Actions', ordering: 'undefined' }
];

interface Props {
  handleSort: (ordering: string, toggleDirection?: boolean) => void;
  descending: boolean;
  sortBy: string;
}

const TableHeader = ({ handleSort, sortBy, descending }: Props) => (
  <thead>
    <tr>
      {TASK_COLUMNS.map((item: TableColumnInfo) => (
        <th
          key={item.name}
          onClick={(item.ordering && item.ordering !== 'undefined') ? () => {
              handleSort(item.ordering, true)
            } : undefined
          }
          className={'th-header' + (item.textAlign ? ` ${item.textAlign}`: '')}
        >
          {item.name}
            {
              (sortBy === item.ordering) &&
              <span>
                &nbsp;
                <i className={'fas fa-arrow-' + (descending ?  'down' : 'up')} />
              </span>

            }
        </th>
      ))}
    </tr>
  </thead>
);

export default TableHeader;
