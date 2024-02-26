import _ from 'lodash';

import {Workflow, WorkflowExecution} from '../../types/domain_types';

import { stringToNullOrInt } from '../../utils';
import { saveWorkflow, makeErrorElement } from '../../utils/api';

import React, { Component, Fragment } from 'react';

import {
  Alert,
  Tab, Tabs
} from 'react-bootstrap';

import * as Yup from 'yup';

import { Formik, Form } from 'formik';

import { GlobalContext } from '../../context/GlobalContext';

import { BootstrapVariant } from '../../types/ui_types';

import ScheduleSelector from '../../components/ScheduleSelector/ScheduleSelector';
import WorkflowNotificationMethods from './WorkflowNotificationMethods';
import WorkflowDetails from '../../components/WorkflowDetails/WorkflowDetails';
import WorkflowSettings from '../../components/WorkflowDetails/WorkflowSettings';

type Props = {
  workflow: Workflow;
  workflowExecution: WorkflowExecution | null;
  onTabChanged?: (tabKey: string | null) => void;
  onWorkflowChanged?: (workflow: Workflow) => void;
};

interface State {
  workflow: Workflow;
  isSaving: boolean;
  flashBody?: any;
  flashAlertVariant?: BootstrapVariant;
}

const workflowSchema = Yup.object().shape({
  name: Yup.string().max(200).required(),
  description: Yup.string().max(1000).nullable(),
  schedule: Yup.string().max(1000).nullable(),
  max_concurrency: Yup.number().integer().positive().nullable(),
  max_age_seconds: Yup.number().integer().positive().nullable(),
  enabled: Yup.boolean()
});

export default class WorkflowEditor extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    this.state = {
      workflow: props.workflow,
      isSaving: false
    };
  }

  public render() {
    const {
      workflowExecution
    } = this.props;

    const {
      workflow,
      isSaving,
      flashBody,
      flashAlertVariant
    } = this.state;

    const initialValues = Object.assign({}, workflow);
    delete initialValues['run_environment'];
    initialValues.runEnvironmentUuid = workflow.run_environment?.uuid;

    return (
      <Fragment>
        {
          flashBody && !isSaving &&
          <Alert
            variant={flashAlertVariant || 'success'}
            onClose={() => {
              this.setState({
                flashBody: null
              });
            }}
            dismissible>
            {flashBody}
          </Alert>
        }

        <Formik
        	initialValues={initialValues}
        	enableReinitialize={true}
        	validationSchema={workflowSchema}
          onSubmit={this.handleSubmit}>
          {(formikProps) => (
            <Fragment>
              {formikProps.status?.msg && <div>{formikProps.status?.msg}</div>}

              <Form>
                <Tabs defaultActiveKey="graph" onSelect={this.handleTabChanged}>
                  <Tab eventKey="graph" title="Graph">
                    <WorkflowDetails
                     workflow={workflow}
                     workflowExecution={workflowExecution ?? undefined}
                     formikProps={formikProps}
                     onWorkflowChanged={this.handleWorkflowChanged} />
                  </Tab>
                  <Tab eventKey="settings" title="Settings">
                    <WorkflowSettings
                     workflow={workflow}
                     formikProps={formikProps}
                     onWorkflowChanged={this.handleWorkflowChanged} />
                  </Tab>
                  <Tab eventKey="schedule" title="Schedule">
                    <ScheduleSelector
                     workflow={workflow}
                     formikProps={formikProps} />
                  </Tab>
                  <Tab eventKey="notification_methods" title="Notification Methods">
                    <WorkflowNotificationMethods formikProps={formikProps} />
                  </Tab>
                </Tabs>
              </Form>
            </Fragment>
          )}
        </Formik>
      </Fragment>
    );
  }

  handleTabChanged = (selectedTab: string | null, event: any) => {
    const {
      onTabChanged
    } = this.props;

    if (onTabChanged) {
      const value = selectedTab ? _.snakeCase(selectedTab) : null;
      onTabChanged(value);
    }
  };

  handleWorkflowChanged = (workflow: Workflow) => {
    const {
      onWorkflowChanged
    } = this.props;

    this.setState({
      workflow
    });

    if (onWorkflowChanged) {
      onWorkflowChanged(workflow);
    }
  };

  handleSubmit = async (values: any, actions: any) => {
    const {
      workflow,
      onWorkflowChanged
    } = this.props;

    const { currentGroup } = this.context;

    const v = Object.assign({}, values);

    if (values.runEnvironmentUuid) {
      v.run_environment = {
        uuid: values.runEnvironmentUuid
      };
    } else {
      v.run_environment = null;
    }

    delete v['runEnvironmentUuid'];

    v.max_concurrency = stringToNullOrInt(v.max_concurrency);
    v.max_age_seconds = stringToNullOrInt(v.max_age_seconds);

    if (!workflow.uuid) {
      v.created_by_group = { id: currentGroup?.id };
    }

    const updatedWorkflow = Object.assign({}, workflow, v);

    actions.setSubmitting(true);

    this.setState({
      isSaving: true
    });

    try {
      const savedWorkflow = await saveWorkflow(updatedWorkflow);
      this.setState({
        isSaving: false,
        flashAlertVariant: 'success',
        flashBody: (
          <div>
            <i className="fas fa-check" />&nbsp;Workflow successfully saved.
          </div>
        )
      });

      this.handleWorkflowChanged(savedWorkflow);
    } catch (ex) {
      const flashBody = makeErrorElement(ex);

      this.setState({
        flashAlertVariant: 'danger',
        flashBody,
        isSaving: false
      });
    } finally {
      actions.setSubmitting(false);
    }
  };
}