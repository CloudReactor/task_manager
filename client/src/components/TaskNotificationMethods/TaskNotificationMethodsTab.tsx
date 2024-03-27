import React from 'react';
import { Task, NotificationMethod } from "../../types/domain_types";

import { FormGroup } from 'react-bootstrap';

import { Formik, Form, FieldArray } from 'formik';
import NotificationMethodSelector from '../common/NotificationMethodSelector';
import CustomButton from '../common/Button/CustomButton';
import styles from './TaskNotificationMethodsTab.module.scss';

interface Props {
  task: Task;
  editTask: (uuid: string, data: any) => Promise<void>
}

const TaskNotificationMethodsTab = ({
  task,
  editTask
}: Props) => {

	return (
    <div className={styles.formContainer}>
      <Formik
        initialValues={task}
        onSubmit={async (values: any) => {
          await editTask(task.uuid, { alert_methods: values.alert_methods });
        }}
      >
        {({ values, submitForm, isSubmitting }) => (
          <Form>
            <div className={styles.formSection}>
              <FormGroup>
                <FieldArray name="alert_methods" render={arrayHelpers => {
                  return (
                    <NotificationMethodSelector
                      key={values.uuid || 'new'}
                      entityTypeLabel="Task"
                      runEnvironmentUuid={task.run_environment?.uuid}
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
            </div>
            <CustomButton className={styles.saveButton}
              color="primary"
              type="submit"
              disabled={isSubmitting}
              label="Save changes"
              inProgress={isSubmitting}
              faIconName="save"
            />

          </Form>
        )}
      </Formik>
    </div>
	);
}

export default TaskNotificationMethodsTab;