import * as C from '../../utils/constants';

import {
  Workflow,
  WorkflowTaskInstance,
  WorkflowTransition,
  WorkflowExecution
} from '../../types/domain_types';

import React, { Component, Fragment }  from 'react';

import {
  Col,
  Row
} from 'react-bootstrap';

import { FormikProps } from 'formik';

import { GlobalContext, accessLevelForCurrentGroup } from '../../context/GlobalContext';

import CustomButton from '../../components/common/Button/CustomButton';
import WorkflowGraphEditor from './WorkflowGraphEditor';

interface Props {
  workflow: Workflow;
  workflowExecution?: WorkflowExecution;
  formikProps: FormikProps<any>;
  onWorkflowChanged?: (workflow: Workflow) => void
}

interface State {
  workflowTaskInstances:  WorkflowTaskInstance[];
  workflowTransitions: WorkflowTransition[];
  pendingSaveUpdate: boolean;
}

class WorkflowDetails extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    const {
      workflow
    } = this.props;

    this.state = {
      workflowTaskInstances: workflow.workflow_task_instances ??
        workflow.workflow_process_types_instances ?? [],
      workflowTransitions: workflow.workflow_transitions,
      pendingSaveUpdate: false
    }
  }

  public render() {
    const {
      workflow,
      workflowExecution,
      formikProps
    } = this.props;

    const accessLevel = accessLevelForCurrentGroup(this.context);

    if (!accessLevel) {
      return null;
    }

    const {
      isSubmitting,
      values
    } = formikProps;

    console.log('WorkflowDetails rendering Workflow')
    console.dir(workflow);

    const mdSize = (accessLevel >= C.ACCESS_LEVEL_DEVELOPER) ? 9 : 12;

    return (
      <Fragment>
        <Row>
          <Col sm={12} md={mdSize}>
            <WorkflowGraphEditor workflow={workflow}
             workflowExecution={workflowExecution}
             runEnvironmentUuid={values.runEnvironmentUuid}
             onGraphChanged={this.handleGraphChanged} />
          </Col>

          {
            (accessLevel >= C.ACCESS_LEVEL_DEVELOPER) && (
              <Col sm={12} md={3}>
                <div className="d-flex flex-column justify-content-start h-100">
                  <div className="p-2">
                    <dl className="row">
                      <dt className="col-sm-5">Create a new node</dt>
                      <dd className="col-sm-7">
                        <span className="py-1 px-2 border rounded mr-1">SHIFT</span>
                        + left-click
                      </dd>
                      <dt className="col-sm-5">Create a new edge</dt>
                      <dd className="col-sm-7"><span className="py-1 px-2 border rounded mr-1">SHIFT</span> + left-click from one node to another</dd>
                      <dt className="col-sm-5">Edit a node or edge</dt>
                      <dd className="col-sm-7">Double-click</dd>
                      <dt className="col-sm-5">Delete a node or edge</dt>
                      <dd className="col-sm-7">Left-click to select node or edge. Hit delete key</dd>
                    </dl>
                    <dl className="row">
                      <CustomButton
                        color="primary"
                        type="submit"
                        disabled={isSubmitting}
                        label="Save changes"
                        inProgress={isSubmitting}
                        faIconName="save"
                        onActionRequested={(action, cbData) => this.handleSubmit()}
                      />
                    </dl>
                  </div>
                </div>
              </Col>
            )
        }
        </Row>
      </Fragment>
    );
  }

  componentDidUpdate(prevProps: Props, prevState: State, snapshot: any) {
    const {
      workflow
    } = this.props;

    const {
      pendingSaveUpdate
    } = this.state;

    console.log('WorkflowDetails: componentDidUpdate, pendingSaveUpdate = ' + pendingSaveUpdate);
    if ((prevProps.workflow !== workflow) && pendingSaveUpdate) {
      console.log('Copying workflow internals after pending save update');
      this.setState({
        workflowTaskInstances: workflow.workflow_task_instances ?? [],
        workflowTransitions: workflow.workflow_transitions,
        pendingSaveUpdate: false
      });
    }
  }

  handleGraphChanged = (
    workflowTaskInstances: WorkflowTaskInstance[],
    workflowTransitions: WorkflowTransition[]) => {
    const {
      workflow,
      onWorkflowChanged
    } = this.props;

    this.setState({
      workflowTaskInstances,
      workflowTransitions
    });

    const updatedWorkflow = Object.assign({}, workflow, {
      workflow_task_instances: workflowTaskInstances,
      workflow_transitions: workflowTransitions
    });

    if (onWorkflowChanged) {
      onWorkflowChanged(updatedWorkflow);
    }
  };

  handleSubmit = async () => {
    const {
      formikProps
    } = this.props;

    this.setState({
      pendingSaveUpdate: true
    });

    return formikProps.submitForm();
  }
}

export default WorkflowDetails;
