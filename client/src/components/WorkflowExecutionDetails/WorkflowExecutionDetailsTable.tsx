import { WorkflowExecution } from '../../types/domain_types';
import {timeDuration, timeFormat} from "../../utils/index";

import React from 'react';
import { Table } from 'react-bootstrap';
import Status from '../Status/Status';

interface Props {
  workflowExecution: WorkflowExecution
}

function createData(name: string, data: any, isDateTime: boolean = false, isUrl: boolean = false, urlLabel: string = '') {
  return { name, data, isDateTime, isUrl, urlLabel };
}

const WorkflowExecutionDetailsTable = ({ workflowExecution }: Props) => {
  const we = workflowExecution;
  const rows = [
    createData('Status',
       <Status status={we.status} isService={false} forExecutionDetail={true} />),
    createData('Started by', we.started_by),
    createData('Started at', we.started_at, true),
    createData('Finished at', we.finished_at, true),
    createData('Duration', timeDuration(we.started_at, we.finished_at)),
    createData('Last heartbeat at', we.last_heartbeat_at, true),
    createData('Failed attempts', we.failed_attempts),
    createData('Timed out attempts', we.timed_out_attempts),
    //createData('PagerDuty notified at ', we.pagerduty_event_sent_at, true),
    //crateData('PagerDuty event severity ', we.pagerduty_event_severity),

  ];

	return (
    <Table striped bordered responsive hover size="sm">
      <tbody>
        {rows.map(row => (
          <tr key={row.name}>
            <td style={{fontWeight: 'bold'}}>
              {row.name}
            </td>
            <td align="left">
              {
                (!row.data && (row.data !== 0))
                ? 'N/A'
                : row.isUrl
                ? <a href={row.data}>{row.urlLabel || row.data}</a>
                : row.isDateTime
                ? timeFormat(row.data, true)
                : row.data
              }
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
	);
}

export default WorkflowExecutionDetailsTable;