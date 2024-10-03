import React, { useContext, useEffect, useState } from 'react';
import { Col, Row } from 'react-bootstrap';
import { FormikProps } from 'formik';
import { GlobalContext, accessLevelForCurrentGroup } from '../../../context/GlobalContext';
import CustomButton from '../../../components/common/Button/CustomButton';
import WorkflowGraphEditor from './WorkflowGraphEditor';
import {
  Workflow,
  WorkflowTaskInstance,
  WorkflowTransition,
  WorkflowExecution
} from '../../../types/domain_types';
import * as C from '../../../utils/constants';

interface Props {
  workflow: Workflow;
  workflowExecution?: WorkflowExecution;
  formikProps: FormikProps<any>;
  onWorkflowChanged?: (workflow: Workflow) => void;
}

const WorkflowGraphTab: React.FC<React.PropsWithChildren<Props>> = ({
  workflow,
  workflowExecution,
  formikProps,
  onWorkflowChanged
}) => {
  const accessLevel = accessLevelForCurrentGroup(useContext(GlobalContext));

  if (accessLevel === null) {
    return null;
  }

  const handleGraphChanged = (
    workflowTaskInstances: WorkflowTaskInstance[],
    workflowTransitions: WorkflowTransition[]
  ) => {
    const updatedWorkflow = {
      ...workflow,
      workflow_task_instances: workflowTaskInstances,
      workflow_transitions: workflowTransitions
    };

    if (onWorkflowChanged) {
      onWorkflowChanged(updatedWorkflow);
    }
  };

  const handleSubmit = async () => {
    const { submitForm } = formikProps;
    return submitForm();
  };

  const mdSize = accessLevel >= C.ACCESS_LEVEL_DEVELOPER ? 9 : 12;

  return (
    <>
      <Row>
        <Col sm={12} md={mdSize}>
          <WorkflowGraphEditor
            workflow={workflow}
            workflowExecution={workflowExecution}
            runEnvironmentUuid={formikProps.values.runEnvironmentUuid}
            onGraphChanged={handleGraphChanged}
          />
        </Col>
        {accessLevel >= C.ACCESS_LEVEL_DEVELOPER && (
          <Col sm={12} md={3}>
            <div className="d-flex flex-column justify-content-start h-100">
              <div className="p-2">
                <dl className="row">
                  <dt className="col-sm-5">Create a new node</dt>
                  <dd className="col-sm-7">
                    <span className="py-1 px-2 border rounded mr-1">SHIFT</span>+ left-click
                  </dd>
                  <dt className="col-sm-5">Create a new edge</dt>
                  <dd className="col-sm-7">
                    <span className="py-1 px-2 border rounded mr-1">SHIFT</span> + left-click from one node to another
                  </dd>
                  <dt className="col-sm-5">Edit a node or edge</dt>
                  <dd className="col-sm-7">Double-click</dd>
                  <dt className="col-sm-5">Delete a node or edge</dt>
                  <dd className="col-sm-7">Left-click to select node or edge. Hit delete key</dd>
                </dl>
                <dl className="row">
                  <CustomButton
                    color="primary"
                    type="submit"
                    disabled={formikProps.isSubmitting}
                    label="Save changes"
                    inProgress={formikProps.isSubmitting}
                    faIconName="save"
                    onActionRequested={(action, cbData) => handleSubmit()}
                  />
                </dl>
              </div>
            </div>
          </Col>
        )}
      </Row>
    </>
  );
};

export default WorkflowGraphTab;
