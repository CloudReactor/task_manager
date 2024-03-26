import * as C from '../../../utils/constants';

import {
  NotificationMethod
} from '../../../types/domain_types';

import React, { useContext }  from 'react';

import { FormikProps, FieldArray } from 'formik';

import {
  FormGroup,
} from "react-bootstrap";

import {
  accessLevelForCurrentGroup,
  GlobalContext
} from '../../../context/GlobalContext';

import NotificationMethodSelector from '../../../components/common/NotificationMethodSelector';
import CustomButton from '../../../components/common/Button/CustomButton';
import styles from './WorkflowSettings.module.scss';

interface Props {
  formikProps: FormikProps<any>;
}

export default function WorkflowNotificationMethods({ formikProps }: Props) {
  const {
    values, submitForm, isSubmitting
  } = formikProps;

  const context = useContext(GlobalContext);
  const accessLevel = accessLevelForCurrentGroup(context);

  if (!accessLevel) {
    return null;
  }

  const canSave = (accessLevel >= C.ACCESS_LEVEL_DEVELOPER);

  return (
    <div className={styles.formContainer}>
      <div className={styles.formSection}>
        <fieldset disabled={!canSave}>
          <FormGroup controlId="forNotifications">
            <FieldArray name="alert_methods" render={arrayHelpers => {
              return (
                <NotificationMethodSelector
                  key={values.uuid || 'new'}
                  entityTypeLabel="Workflow"
                  runEnvironmentUuid={values.runEnvironmentUuid}
                  selectedNotificationMethodUuids={values.alert_methods.map(am => am.uuid)}
                  onSelectedNotificationMethodsChanged={(alertMethods: NotificationMethod[]) => {
                    let removed: (NotificationMethod | undefined);
                    do {
                      removed = arrayHelpers.remove(0);
                    } while (removed);
                    alertMethods.forEach(am => {
                      arrayHelpers.push({uuid: am.uuid});
                    });
                }}
                />
              );
            }} />
          </FormGroup>
          {
            canSave && (
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
        </fieldset>
      </div>
    </div>
  );
}
