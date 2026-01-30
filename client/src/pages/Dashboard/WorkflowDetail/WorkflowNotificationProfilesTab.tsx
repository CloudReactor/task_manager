import * as C from '../../../utils/constants';

import {
  NotificationProfile
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

import NotificationProfileSelector from '../../../components/common/NotificationProfileSelector';
import CustomButton from '../../../components/common/Button/CustomButton';
import styles from './WorkflowSettings.module.scss';

interface Props {
  formikProps: FormikProps<any>;
}

export default function WorkflowNotificationProfilesTab({ formikProps }: Props) {
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
          <FormGroup controlId="forNotificationProfiles">
            <FieldArray name="notification_profiles" render={arrayHelpers => {
              return (
                <NotificationProfileSelector
                  key={values.uuid || 'new'}
                  entityTypeLabel="Workflow"
                  runEnvironmentUuid={values.runEnvironmentUuid}
                  selectedNotificationProfileUuids={values.notification_profiles.map(np => np.uuid)}
                  onSelectedNotificationProfilesChanged={(notificationProfiles: NotificationProfile[]) => {
                    let removed: (NotificationProfile | undefined);
                    do {
                      removed = arrayHelpers.remove(0);
                    } while (removed);
                    notificationProfiles.forEach(np => {
                      arrayHelpers.push({uuid: np.uuid});
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
