import * as C from '../../utils/constants';

import { Workflow } from '../../types/domain_types';

import React, { useContext } from 'react';

import {
  Alert,
  Form
} from 'react-bootstrap';

import { Field, FormikProps } from 'formik';

import {
  accessLevelForCurrentGroup,
  GlobalContext
} from '../../context/GlobalContext';

import CustomInput from '../forms/CustomInput';
import FormikErrorsSummary from '../common/FormikErrorsSummary';
import RunEnvironmentSelector from '../common/RunEnvironmentSelector';
import CustomButton from '../common/Button/CustomButton';
import SettingsForm from '../forms/SettingsForm';
import Items from './WorkflowSettingsItems';
import styles from './WorkflowSettings.module.scss';

import CustomInputStyles from '../forms/CustomInput.module.scss';

interface Props {
  workflow: Workflow;
  onWorkflowChanged: (workflow: Workflow) => void;
  formikProps: FormikProps<any>
}

const WorkflowSettings = ({ workflow, formikProps }: Props) => {
  const {
    errors, handleChange, handleBlur, values, setValues,
    touched, submitForm, isSubmitting
  } = formikProps;

  const context = useContext(GlobalContext);
  const accessLevel = accessLevelForCurrentGroup(context);
  const isSaveAllowed = accessLevel && (accessLevel >= C.ACCESS_LEVEL_DEVELOPER);

  const {
    currentGroup
  } = context;

  if (!currentGroup) {
    return <div>Not Found</div>;
  }

  const handleRunEnvironmentUuidChange = (uuid: string | null) => {
    setValues(Object.assign({}, values, {
      runEnvironmentUuid: uuid
    }));
  }


  return (
    <div className={styles.formContainer}>
      {
        (Object.keys(errors).length > 0) &&
        <Alert variant="warning" className="mt-4">
          <FormikErrorsSummary errors={errors}
            touched={touched}
            values={values} />
        </Alert>
      }

      <fieldset disabled={!isSaveAllowed}>
        <Field
          key="control-name-element-1"
          name="name"
          type="text"
          label="Name"
          controlId="forName"
          placeholder=""
          component={CustomInput}
          subText="Enter a name for the Workflow. Note the name must not conflict with your existing Workflow names."
          onChange={handleChange}
        />

        <Form.Label>Run Environment</Form.Label>
        <RunEnvironmentSelector name="runEnvironmentUuid"
         groupId={currentGroup.id}
         selectedUuid={values.runEnvironmentUuid}
         noSelectionText="Unscoped" onChange={handleRunEnvironmentUuidChange} />
        <Form.Text className={CustomInputStyles.subText}>
          Select an optional Run Environment to scope this Workflow to.
          If selected, clients using an API key scoped to a different Run Environment won&apos;t be
          able to access this Workflow. Also, all Tasks and Notification Methods
          associated with this Workflow must be scoped to the same
          Run Environment.
        </Form.Text>

        <SettingsForm items={Items} onChange={handleChange}
         onBlur={handleBlur} />
      </fieldset>

      {
        isSaveAllowed && (
          <CustomButton
            color="primary"
            type="button"
            disabled={isSubmitting}
            label="Save changes"
            inProgress={isSubmitting}
            faIconName="save"
            onActionRequested={(action, cbData) => submitForm()}
          />
        )
      }
    </div>
  );
}

export default WorkflowSettings;
