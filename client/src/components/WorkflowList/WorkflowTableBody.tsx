import React from 'react';
import { useHistory } from 'react-router-dom';

import { Switch } from '@material-ui/core';

import { WorkflowSummary } from '../../types/domain_types';

import * as C from "../../utils/constants";
import { colorPicker, timeFormat, timeDuration } from '../../utils/index';
import Status from '../Status/Status'
import ActionButton from "../common/ActionButton";

import "../../styles/tableStyles.scss";

type Props = {
  workflowPage: WorkflowSummary[];
  handleEditRequest: (workflow: WorkflowSummary, data: any) => Promise<void>;
  handleDeletionRequest: (workflow: WorkflowSummary) => void;
  handleStartRequest: (workflow: WorkflowSummary) => Promise<void>;
  handleStopRequest: (workflow: WorkflowSummary) => Promise<void>;
}

const WorkflowTableBody = ({
	workflowPage,
	handleEditRequest,
	handleDeletionRequest,
	handleStartRequest,
	handleStopRequest
}: Props) => {
  const history = useHistory();

	const handleActionRequested = (action: string | undefined, cbData: any) => {
	  switch (action) {
	    case 'start':
		    handleStartRequest(cbData);
		    break;

	    case 'stop':
		    handleStopRequest(cbData);
		    break;

	    default:
		    console.error(`Unknown action: "${action}"`);
		    break;
	  }
	};

	return (
		<tbody>
	    {
	      workflowPage.map(workflow => {
	        const latestExecution = workflow.latest_workflow_execution;
	        const statusClassName = latestExecution ? colorPicker(latestExecution.status, false) : '';

	        // TODO: link to workflow execution page
	        const pushToExecution = () => history.push(`/workflows/${workflow.uuid}`, { workflow });

	        return (
	          <tr key={workflow.uuid} className="custom_status_bg">
	            <td onClick={pushToExecution}>
	                { workflow.name }
	            </td>
	            <td className="text-center pointer">
                <Switch
                	color="primary"
                	checked={workflow.enabled}
                	onChange={event => {handleEditRequest(workflow, { enabled: event.target.checked } )}}
              	/>
	            </td>
	            <td className={statusClassName} onClick={pushToExecution}>
	              { (workflow && workflow.latest_workflow_execution)
	                ? <Status isService={false} status={workflow.latest_workflow_execution.status}
	                   forExecutionDetail={false} />
	                : 'Never run'}
	            </td>
	            <td onClick={pushToExecution}>
	              { latestExecution ? timeFormat(latestExecution.started_at) : 'Never started'}
	            </td>
	            <td onClick={pushToExecution}>
	              { latestExecution && (latestExecution.finished_at ? timeFormat(latestExecution.finished_at) : 'In Progress')}
	            </td>
	            <td onClick={pushToExecution}>
	              { latestExecution && timeDuration(latestExecution.started_at, latestExecution.finished_at) }
	            </td>
	            <td align="right" onClick={pushToExecution}>
	              { latestExecution && latestExecution.failed_attempts }
	            </td>
	            <td onClick={pushToExecution}>
	              { workflow.schedule }
	            </td>
	            <td>
	              <ActionButton
									action="start"
									label="Start"
									cbData={workflow}
									faIconName="play"
									onActionRequested={handleActionRequested}
								/>
	              <ActionButton
									action="stop"
									label="Stop"
									cbData={workflow}
									disabled={!workflow.latest_workflow_execution || (workflow.latest_workflow_execution.status !== C.WORKFLOW_EXECUTION_STATUS_RUNNING)}
									faIconName="stop"
									onActionRequested={handleActionRequested}
									color="secondary"
								/>
	              <i
									className="fas fa-trash"
									onClick={() => handleDeletionRequest(workflow)}
									style={{ paddingLeft: '5px'}}
								/>
	            </td>
	          </tr>
	        );
	      })
	    }
	  </tbody>
	);
};

export default WorkflowTableBody;