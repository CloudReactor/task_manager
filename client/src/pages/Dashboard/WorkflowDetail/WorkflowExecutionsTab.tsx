import {
  Workflow, WorkflowExecution
} from '../../../types/domain_types';

import React, { Fragment } from 'react';

import Charts from './Charts';
import WorkflowExecutionsTable from './WorkflowExecutionsTable';

interface Props {
  workflow: Workflow;
  onActionError: (action: string, cbData: any, errorMessage: string) => void;
  onWorkflowExecutionUpdated: (execution: WorkflowExecution) => void;
}

const WorkflowExecutionsTab = (props: Props) => {
  const {
    workflow
  } = props;

  return (workflow && workflow.latest_workflow_execution) ? (
    <Fragment>
      <Charts uuid={workflow.uuid} />
      <section>
        <hr/>
        <WorkflowExecutionsTable
          workflow={workflow}
          onActionError={props.onActionError}
          onWorkflowExecutionUpdated={props.onWorkflowExecutionUpdated} />
      </section>
    </Fragment>
  ) : (
    <h2 className="mt-5">
      This Workflow has not run yet. When it does, you&apos;ll be able to see
      a table of Workflow Executions here.
    </h2>
  );

};

export default WorkflowExecutionsTab;