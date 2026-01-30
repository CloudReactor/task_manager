import _ from 'lodash';

import * as Yup from 'yup';

import { stringToNullOrInt } from '../../../utils';
import { saveWorkflow, makeErrorElement } from '../../../utils/api';
import { Workflow, WorkflowExecution } from '../../../types/domain_types';

import React, { useContext, useState } from 'react';

import {
  Alert,
  Tab,
  Tabs
} from 'react-bootstrap';


import { Formik, Form } from 'formik';

import { GlobalContext } from '../../../context/GlobalContext';

import { BootstrapVariant } from '../../../types/ui_types';

import WorkflowExecutionsTab from './WorkflowExecutionsTab';
import ScheduleSelector from '../../../components/ScheduleSelector/ScheduleSelector';
import WorkflowNotificationMethodsTab from './WorkflowNotificationMethodsTab';
import WorkflowNotificationProfilesTab from './WorkflowNotificationProfilesTab';
import WorkflowGraphTab from './WorkflowGraphTab';
import WorkflowSettingsTab from './WorkflowSettingsTab';


import styles from './WorkflowEditor.module.scss';

type Props = {
  workflow: Workflow;
  workflowExecution: WorkflowExecution | null;
  tab?: string;
  onTabChanged?: (tabKey: string | null) => void;
  onWorkflowChanged?: (workflow: Workflow) => void;
  onActionError: (action: string, cbData: any, errorMessage: string) => void;
  onWorkflowExecutionUpdated: (execution: WorkflowExecution) => void;
};

const WorkflowEditor: React.FC<React.PropsWithChildren<Props>> = (props) => {
  const { currentGroup } = useContext(GlobalContext);
  const [workflow, setWorkflow] = useState<Workflow>(props.workflow);
  const [isSaving, setIsSaving] = useState(false);
  const [flashBody, setFlashBody] = useState<any>();
  const [flashAlertVariant, setFlashAlertVariant] = useState<BootstrapVariant>();

  const workflowSchema = Yup.object().shape({
    name: Yup.string().max(200).required(),
    description: Yup.string().max(1000).nullable(),
    schedule: Yup.string().max(1000).nullable(),
    max_concurrency: Yup.number().integer().positive().nullable(),
    max_age_seconds: Yup.number().integer().positive().nullable(),
    enabled: Yup.boolean()
  });

  const handleTabChanged = (selectedTab: string | null, event: any) => {
    const { onTabChanged } = props;
    if (onTabChanged) {
      const value = selectedTab ? _.snakeCase(selectedTab) : null;
      onTabChanged(value);
    }
  };

  const handleWorkflowChanged = (workflow: Workflow) => {
    const { onWorkflowChanged } = props;
    setWorkflow(workflow);
    if (onWorkflowChanged) {
      onWorkflowChanged(workflow);
    }
  };

  const handleSubmit = async (values: any, actions: any) => {
    const { workflow } = props;
    const v = { ...values };
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
    const updatedWorkflow = { ...workflow, ...v };
    actions.setSubmitting(true);
    setIsSaving(true);
    try {
      const savedWorkflow = await saveWorkflow(updatedWorkflow);
      setIsSaving(false);
      setFlashAlertVariant('success');
      setFlashBody(
        <div>
          <i className="fas fa-check" />&nbsp;Workflow successfully saved.
        </div>
      );
      handleWorkflowChanged(savedWorkflow);
    } catch (ex) {
      const flashBody = makeErrorElement(ex);
      setFlashAlertVariant('danger');
      setFlashBody(flashBody);
      setIsSaving(false);
    } finally {
      actions.setSubmitting(false);
    }
  };

  const {
    workflowExecution,
    tab,
    onActionError,
    onWorkflowExecutionUpdated
  } = props;

  const initialValues = { ...workflow };
  delete initialValues['run_environment'];
  initialValues.runEnvironmentUuid = workflow.run_environment?.uuid;

  return (
    <>
      {flashBody && !isSaving && (
        <Alert
          variant={flashAlertVariant || 'success'}
          onClose={() => {
            setFlashBody(null);
          }}
          dismissible
        >
          {flashBody}
        </Alert>
      )}

      <Formik
        initialValues={initialValues}
        enableReinitialize={true}
        validationSchema={workflowSchema}
        onSubmit={handleSubmit}
      >
        {(formikProps) => (
          <>
            {formikProps.status?.msg && <div>{formikProps.status?.msg}</div>}

            <Form>
              <Tabs defaultActiveKey={tab} onSelect={handleTabChanged}>
                <Tab eventKey="executions" title="Executions" className={styles.tabContainer}>
                  <WorkflowExecutionsTab workflow={workflow}
                   onActionError={onActionError}
                   onWorkflowExecutionUpdated={onWorkflowExecutionUpdated}
                  />
                </Tab>
                <Tab eventKey="graph" title="Graph">
                  <WorkflowGraphTab
                    workflow={workflow}
                    workflowExecution={workflowExecution ?? undefined}
                    formikProps={formikProps}
                    onWorkflowChanged={handleWorkflowChanged}
                  />
                </Tab>
                <Tab eventKey="settings" title="Settings" className={styles.tabContainer}>
                  <WorkflowSettingsTab
                    workflow={workflow}
                    formikProps={formikProps}
                    onWorkflowChanged={handleWorkflowChanged}
                  />
                </Tab>
                <Tab eventKey="schedule" title="Schedule" className={styles.tabContainer}>
                  <ScheduleSelector
                    workflow={workflow}
                    formikProps={formikProps}
                    />
                </Tab>
                <Tab eventKey="notification_profiles" title="Notification Profiles"
                 className={styles.tabContainer}>
                  <WorkflowNotificationProfilesTab formikProps={formikProps} />
                </Tab>
                <Tab eventKey="notification_methods" title="Notification Methods (legacy)"
                 className={styles.tabContainer}>
                  <WorkflowNotificationMethodsTab formikProps={formikProps} />
                </Tab>
              </Tabs>
            </Form>
          </>
        )}
      </Formik>
    </>
  );
};

export default WorkflowEditor;
