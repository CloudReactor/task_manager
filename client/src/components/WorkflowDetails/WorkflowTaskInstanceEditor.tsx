
import {EntityReference, Task, WorkflowTaskInstance} from '../../types/domain_types';
import * as C from '../../utils/constants'
import { fetchTasks } from '../../utils/api';

import React, { Component, Fragment } from 'react';

import {
  Form as BootstrapForm
} from 'react-bootstrap';

import { Formik, Form, Field, ErrorMessage } from 'formik';

import * as Yup from 'yup';

import Modal from 'react-bootstrap/Modal';
import Button from 'react-bootstrap/Button';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

interface Props {
  workflowTaskInstance: WorkflowTaskInstance | null;
  runEnvironmentUuid: string | null;
  size?: string;
  isOpen: boolean;
  onSave: (wti: any) => void;
  onCancel: () => void;
}

interface State {
  open: boolean;
  workflowTaskInstance: any;
  tasks: EntityReference[] | null;
  uuidsToTasks: any;
}


const WorkflowTaskInstanceSchema = Yup.object().shape({
  name: Yup.string()
    .max(50, 'Name is too long')
    .required('Name is required'),
  taskUuid: Yup.string()
    .required('Task is required'),
  startTransitionCondition: Yup.string()
    .required('Start transition condition is required'),
  failureBehavior: Yup.string().required('Failure behavior is required'),
  allowWorkflowExecutionAfterFailure: Yup.boolean(),
  timeoutBehavior: Yup.string().required('Timeout behavior is required'),
  allowWorkflowExecutionAfterTimeout: Yup.boolean(),
});


export default class WorkflowTaskInstanceEditor extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    this.state = {
      open: props.isOpen,
      workflowTaskInstance: props.workflowTaskInstance ?? {},
      tasks: [],
      uuidsToTasks: {}
    };
  }

  static getDerivedStateFromProps(props, state) {
    return {
      open: props.isOpen,
      workflowTaskInstance: props.workflowTaskInstance ?? {}
    };
  }

  componentDidUpdate(prevProps: any) {
    if (prevProps.runEnvironmentUuid !== this.props.runEnvironmentUuid) {
      this.loadTasks();
    }
  }

  handleOpen = () => {
    this.setState({ open: true });
  }

  handleClose = () => {
    this.setState({ open: false });
  }

  toggle = () => {
    this.props.onCancel();
  }

  async componentDidMount() {
    await this.loadTasks();
  }

  public render() {
    const {
      runEnvironmentUuid
    } = this.props;

    const accessLevel = accessLevelForCurrentGroup(this.context);
    const canSave = accessLevel && (accessLevel >= C.ACCESS_LEVEL_DEVELOPER);

    const {
      open,
      workflowTaskInstance,
      tasks,
      uuidsToTasks
    } = this.state;

    const name = workflowTaskInstance?.name ?? '';
    const taskUuid = workflowTaskInstance?.task?.uuid ?? '';
    const startTransitionCondition = workflowTaskInstance?.start_transition_condition ?? 'any';
    const failureBehavior = workflowTaskInstance.failure_behavior ?? C.TASK_FAILURE_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED;
    const timeoutBehavior = workflowTaskInstance.timeout_behavior ?? C.TASK_EXECUTION_STATUS_FAIL_WORKFLOW_IF_UNHANDLED;
    const allowWorkflowExecutionAfterFailure = workflowTaskInstance.allow_workflow_execution_after_failure ?? false;
    const allowWorkflowExecutionAfterTimeout = workflowTaskInstance.allow_workflow_execution_after_timeout ?? false;

    return (
      <Modal show={open} onHide={this.toggle}>

        <Modal.Header closeButton>
          <Modal.Title>
            Task configuration
          </Modal.Title>
        </Modal.Header>

        <Formik
         initialValues={ {name,taskUuid, startTransitionCondition, failureBehavior, timeoutBehavior,
                          allowWorkflowExecutionAfterFailure, allowWorkflowExecutionAfterTimeout} }
         enableReinitialize={true}
         validationSchema={WorkflowTaskInstanceSchema}
         onSubmit={(values, actions) => {
           console.log('onSubmit, values = ');
           console.dir(values);
           //console.log('onSubmit, values = ');
           //console.dir(actions);

           const wti = workflowTaskInstance || {};
           wti.name = values.name;
           wti.task = {
             uuid: values.taskUuid,
             name: uuidsToTasks[values.taskUuid].name
           };
           wti.start_transition_condition = values.startTransitionCondition;
           wti.failure_behavior = values.failureBehavior;
           wti.allow_workflow_execution_after_failure = values.allowWorkflowExecutionAfterFailure;
           wti.timeout_behavior = values.timeoutBehavior;
           wti.allow_workflow_execution_after_timeout = values.allowWorkflowExecutionAfterTimeout;

           this.handleSave(wti);
         }}>
          {({ errors, status, touched, submitForm, isSubmitting }) => (
          <Form>
            <Modal.Body>
              <fieldset disabled={!canSave}>
                <div className="form-group">
                  <label>Name</label>
                  <Field name="name" className="form-control" />
                  <ErrorMessage name="name" component="span" className="help-block" />
                </div>

                <div className="form-group">
                  <label>Task</label>
                  <Field name="taskUuid"
                        component="select" className="form-control">
                    <option value="" key="">Select a Task</option>
                    {
                      tasks && tasks.map(task => {
                        return (
                          <option value={task.uuid} key={task.uuid}>
                            {task.name}
                          </option>
                        );
                      })
                    }
                  </Field>
                  {
                    tasks && (tasks.length === 0) && (
                      <BootstrapForm.Text>
                        {
                          runEnvironmentUuid ? (
                            <Fragment>
                              No Tasks were found in the scoped Run Environment.
                              Try another Run Environment or leave the Workflow unscoped.
                            </Fragment>
                          ) : (
                            <Fragment>
                              No Tasks were found.
                            </Fragment>
                          )
                        }
                      </BootstrapForm.Text>
                    )
                  }
                  <ErrorMessage name="taskUuid" component="span" className="help-block" />
                </div>
                <div className="form-group">
                  <label>Required Transitions to Start</label>
                  <Field name="startTransitionCondition" component="select" className="form-control">
                    <option value={C.START_TRANSITION_CONDITIONS_ANY}>Any Incoming Transition</option>
                    <option value={C.START_TRANSITION_CONDITIONS_ALL}>All Incoming Transitions</option>
                  </Field>
                  <ErrorMessage name="start_transition_condition" component="span" className="help-block" />
                </div>
                <div className="form-group">
                  <label>On Failure</label>
                  <Field name="failureBehavior" component="select" className="form-control">
                    <option value={C.TASK_FAILURE_BEHAVIOR_FAIL_WORKFLOW_ALWAYS}>Always Fail Workflow</option>
                    <option value={C.TASK_FAILURE_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED}>Fail Workflow if Unhandled</option>
                    <option value={C.TASK_FAILURE_BEHAVIOR_IGNORE}>Ignore Failure</option>
                  </Field>
                </div>

                <div className="checkbox">
                  <label>
                    <Field name="allowWorkflowExecutionAfterFailure" type="checkbox" />
                    &nbsp;Allow Workflow execution to continue after failure
                  </label>
                </div>

                <div className="form-group">
                  <label>On Timeout</label>
                  <Field name="timeoutBehavior" component="select" className="form-control">
                    <option value={C.TASK_EXECUTION_STATUS_FAIL_WORKFLOW_ALWAYS}>Always Fail Workflow</option>
                    <option value={C.TASK_EXECUTION_STATUS_FAIL_WORKFLOW_IF_UNHANDLED}>Fail Workflow if Unhandled</option>
                    <option value={C.TASK_EXECUTION_STATUS_TIMEOUT_WORKFLOW_ALWAYS}>Always Timeout Workflow</option>
                    <option value={C.TASK_EXECUTION_STATUS_TIMEOUT_WORKFLOW_IF_UNHANDLED}>Timeout Workflow if Unhandled</option>
                    <option value={C.TASK_EXECUTION_STATUS_IGNORE}>Ignore Timeout</option>
                  </Field>
                </div>

                <div className="checkbox">
                  <label>
                    <Field name="allowWorkflowExecutionAfterTimeout" type="checkbox" />
                    &nbsp;Allow Workflow execution to continue after timeout
                  </label>
                </div>
              </fieldset>
            </Modal.Body>

            <Modal.Footer>
              <Button variant="secondary" onClick={this.toggle}>
                { canSave ? 'Cancel' : 'Close' }
              </Button>

              {
                canSave && (
                  <Button variant="primary" onClick={submitForm}>
                    {
                      this.props.workflowTaskInstance ?
                      (isSubmitting ? 'Updating ...' : 'Update') :
                      (isSubmitting ? 'Adding ...' : 'Add')
                    }
                  </Button>
                )
              }
            </Modal.Footer>
          </Form>
        )}
        </Formik>
      </Modal>
    );
  }

  handleTaskChange = (event: any) => {
    console.log('handleTaskChange');

  }

  handleSave = (wti: any) => {
    console.log('handleSave');
    console.dir(wti);

    this.setState({
      workflowTaskInstance: this.props.workflowTaskInstance || {},
    }, () => {
      this.props.onSave(wti);
    });
  }

  async loadTasks() {
    const {
      runEnvironmentUuid
    } = this.props;

    const pageSize = 100;
    let tasks: Task[] = [];
    let offset = 0;
    let done = false;
    const { currentGroup } = this.context;

    while (!done) {
      const page = await fetchTasks({
        selectedRunEnvironmentUuid: runEnvironmentUuid || undefined,
        sortBy: 'name',
        offset,
        maxResults: pageSize,
        groupId: currentGroup?.id,
        isService: false,
        otherParams: {
          fields: 'uuid,name',
          passive: false
        }
      });
      tasks = tasks.concat(page.results);

      done = page.results.length < pageSize;
      offset += pageSize;
    }
    const uuidsToTasks: any = {};

    tasks.forEach(pt => {
      uuidsToTasks[pt.uuid] = pt;
    });

    this.setState({
      tasks,
      uuidsToTasks
    });
  }
}
