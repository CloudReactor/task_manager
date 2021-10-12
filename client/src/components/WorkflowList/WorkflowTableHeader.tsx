import React from 'react';
import { TableColumnInfo } from "../../types/ui_types";
import "../../styles/tableStyles.scss";

interface Props {
  handleSort: (ordering: string, toggleDirection?: boolean) => void;
  sortBy: string;
  descending: boolean;
}

const WORKFLOW_COLUMNS: TableColumnInfo[] = [
  { name: 'Name', ordering: 'name' },
  { name: 'Enabled', ordering: 'enabled', textAlign: 'text-center' },
  { name: 'Status', ordering: 'latest_workflow_execution__status' },
  { name: 'Started', ordering: 'latest_workflow_execution__started_at' },
  { name: 'Finished', ordering: 'latest_workflow_execution__finished_at' },
  { name: 'Duration', ordering: 'undefined' },
  { name: 'Failed Attempts', ordering: 'undefined' },
  { name: 'Schedule', ordering: 'schedule' },
  { name: 'Actions', ordering: 'undefined' }
];

const WorkflowTableHeader = ({ handleSort, sortBy, descending }: Props) => (
	<thead>
	  <tr>
	    {
	      WORKFLOW_COLUMNS.map((item: TableColumnInfo) => {
	        return (
	          <th
              key={item.name}
              onClick={(item.ordering && item.ordering !== 'undefined') ? () => {
                  handleSort(item.ordering, true)
                } : undefined
              }
              className={'th-header' + (item.textAlign ? ` ${item.textAlign}`: '')}
          	>
	            { item.name }
              {
                (sortBy === item.ordering) &&
                <span>
                  &nbsp;
                  <i className={'fas fa-arrow-' + (descending ?  'down' : 'up')} />
                </span>
              }
	          </th>
	        );
	      })
	    }
	  </tr>
	</thead>
);

export default WorkflowTableHeader;