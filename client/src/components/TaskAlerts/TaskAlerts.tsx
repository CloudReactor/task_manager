import React from 'react';
import { Task, AlertMethod } from "../../types/domain_types";

import { FormGroup } from 'react-bootstrap';

import { Formik, Form, FieldArray } from 'formik';
import AlertMethodSelector from '../common/AlertMethodSelector';
import CustomButton from '../common/Button/CustomButton';
import styles from './TaskAlerts.module.scss';

interface Props {
  task: Task;
  editTask: (uuid: string, data: any) => Promise<void>
}

const TaskAlerts = ({
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
              <div className={styles.sectionTitle}>
                Select Alert Methods to use with this Task
              </div>
              <FormGroup>
                <FieldArray name="alert_methods" render={arrayHelpers => {
                  return (
                    <AlertMethodSelector
                      key={values.uuid || 'new'}
                      entityTypeLabel="Task"
                      runEnvironmentUuid={task.run_environment?.uuid}
                      selectedAlertMethodUuids={values.alert_methods.map(am => am.uuid)}
                      onSelectedAlertMethodsChanged={(alertMethods: AlertMethod[]) => {
                        let removed: (AlertMethod | undefined);
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
            <CustomButton
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

export default TaskAlerts;