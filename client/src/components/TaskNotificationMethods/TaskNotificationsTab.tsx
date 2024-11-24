import _ from 'lodash';
import pluralize from 'pluralize';

import React, { Fragment, useState } from 'react';

import * as Yup from 'yup';

import { Task, NotificationMethod } from "../../types/domain_types";

import {
  Form, FormCheck, FormControl, FormGroup, FormLabel, FormText,
  InputGroup,
  Row, Col, Container
} from 'react-bootstrap';

import {
  Formik,
  FieldArray
} from 'formik';

import NotificationMethodSelector from '../common/NotificationMethodSelector';
import CustomButton from '../common/Button/CustomButton';
import styles from './TaskNotificationsTab.module.scss';
import NotificationEventSeveritySelector from '../common/NotificationEventSeveritySelector/NotificationEventSeveritySelector';

interface Props {
  task: Task;
  onTaskSaved: (uuid: string, data: any) => Promise<void>;
}

const schema = Yup.object().shape({
  notification_event_severity_on_success: Yup.number().min(0).integer().nullable(),
  notification_event_severity_on_failure: Yup.number().min(0).integer().nullable(),
  notification_event_severity_on_timeout: Yup.number().min(0).integer().nullable(),
  notification_event_severity_on_missing_execution: Yup.number().min(0).integer().nullable(),
  notification_event_severity_on_missing_heartbeat: Yup.number().min(0).integer().nullable(),
  notification_event_severity_on_service_down: Yup.number().min(0).integer().nullable(),
  max_postponed_failure_count: Yup.number().min(0).integer().nullable(),
  postponed_failure_before_success_seconds: Yup.number().min(0).integer().nullable(),
  required_success_count_to_clear_failure: Yup.number().min(1).integer().nullable(),
  max_postponed_timeout_count: Yup.number().min(0).integer().nullable(),
  postponed_timeout_before_success_seconds: Yup.number().min(0).integer().nullable(),
  required_success_count_to_clear_timeout: Yup.number().min(1).integer().nullable(),
});

const TaskNotificationsTab = ({
  task,
  onTaskSaved
}: Props) => {

  const [prevPostponedFailureBeforeSuccessSeconds, setPrevPostponedFailureBeforeSuccessSeconds] =
    useState(task.postponed_failure_before_success_seconds);

  const [prevPostponedTimeoutBeforeSuccessSeconds, setPrevPostponedTimeoutBeforeSuccessSeconds] =
    useState(task.postponed_timeout_before_success_seconds);

	return (
    <Container fluid={true} className={styles.formContainer}>
      <Formik
        validationSchema={schema}
        initialValues={task}
        onSubmit={async (values: Task) => {
          if (values.postponed_failure_before_success_seconds === null) {
            values.max_postponed_failure_count = null;
            values.required_success_count_to_clear_failure = null;
          }

          if (values.postponed_timeout_before_success_seconds === null) {
            values.max_postponed_timeout_count = null;
            values.required_success_count_to_clear_timeout = null;
          }

          await onTaskSaved(task.uuid, _.pick(values,
            'notification_event_severity_on_success',
            'notification_event_severity_on_failure',
            'notification_event_severity_on_timeout',
            'notification_event_severity_on_missing_execution',
            'notification_event_severity_on_missing_heartbeat',
            'notification_event_severity_on_service_down',
            'max_postponed_failure_count',
            'postponed_failure_before_success_seconds',
            'required_success_count_to_clear_failure',
            'max_postponed_timeout_count',
            'postponed_timeout_before_success_seconds',
            'required_success_count_to_clear_timeout',
            'alert_methods'));
        }}
      >
        {({ values, setFieldValue, errors, handleChange, handleSubmit, isSubmitting }) => {


          const disabledFailureNotifications = (values.notification_event_severity_on_failure === null);
          const immediateFailureNotifications = (values.postponed_failure_before_success_seconds === null);
          const postponedFailureTextClassName = (disabledFailureNotifications || immediateFailureNotifications) ?
            'text-muted' : '';

          const enablePostponedFailureNotifications = (_event) => {
            console.log('postponed')
            setFieldValue('postponed_failure_before_success_seconds',
              values.postponed_failure_before_success_seconds ?? prevPostponedFailureBeforeSuccessSeconds ?? (30 * 60));
            setFieldValue('max_postponed_failure_count',
              values.max_postponed_failure_count ?? 1);
            setFieldValue('required_success_count_to_clear_failure',
              values.required_success_count_to_clear_failure ?? 1);
          };

          const disablePostponedFailureNotifications = (_event) => {
            console.log('immediate');
            setPrevPostponedFailureBeforeSuccessSeconds(values.postponed_failure_before_success_seconds);
            setFieldValue('postponed_failure_before_success_seconds', null);
          };

          const disabledTimeoutNotifications = (values.notification_event_severity_on_timeout === null);
          const immediateTimeoutNotifications = (values.postponed_timeout_before_success_seconds === null);
          const postponedTimeoutTextClassName = (disabledTimeoutNotifications || immediateTimeoutNotifications) ?
            'text-muted' : '';

          const enablePostponedTimeoutNotifications = (_event) => {
            setFieldValue('postponed_timeout_before_success_seconds',
              values.postponed_timeout_before_success_seconds ?? prevPostponedTimeoutBeforeSuccessSeconds ?? (30 * 60));
            setFieldValue('max_postponed_timeout_count',
              values.max_postponed_timeout_count ?? 1);
            setFieldValue('required_success_count_to_clear_timeout',
              values.required_success_count_to_clear_timeout ?? 1);
          };

          const disablePostponedTimeoutNotifications = (_event) => {
            setPrevPostponedTimeoutBeforeSuccessSeconds(values.postponed_timeout_before_success_seconds);
            setFieldValue('postponed_timeout_before_success_seconds', null);
          };

          return (
            <Fragment>
              <div className={styles.formSection}>
                <Form>
                  <fieldset>
                    <Row>
                      <Col>
                        <legend>Failure Notifications</legend>
                      </Col>
                    </Row>

                    <FormGroup>
                      <Row>
                        <Col sm={4} md={3} className={styles.labelColumn}>
                          <FormLabel>Severity level</FormLabel>
                        </Col>
                        <Col>
                          <NotificationEventSeveritySelector selectedSeverity={values.notification_event_severity_on_failure}
                           onSelectedSeverityChanged={ (severity) =>
                            setFieldValue('notification_event_severity_on_failure', severity)
                           }/>
                        </Col>
                      </Row>
                    </FormGroup>

                    <FormGroup>
                      <Row>
                        <Col>
                          <FormCheck id="immediate_failure_notifications_checkbox"
                            type="radio" label="Send failure notifications immediately"
                            disabled={isSubmitting || disabledFailureNotifications}
                            checked={immediateFailureNotifications}
                            onChange={disablePostponedFailureNotifications} />
                        </Col>
                      </Row>
                    </FormGroup>
                    <FormGroup>
                      <Row className="mb-3">
                        <Col>
                          <FormCheck id="postpone_failure_notifications_checkbox"
                            type="radio" label="Postpone failure notifications for"
                            disabled={isSubmitting || disabledFailureNotifications}
                            checked={!immediateFailureNotifications}
                            onChange={enablePostponedFailureNotifications}>
                          </FormCheck>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <InputGroup className={styles.inputGroupWithUnit}>
                            <FormControl type="number" name="postponed_failure_before_success_seconds"
                              value={values.postponed_failure_before_success_seconds ?? ''}
                              min="0" step="1" onChange={handleChange}
                              disabled={disabledFailureNotifications || immediateFailureNotifications || isSubmitting}
                              isInvalid={!!errors.postponed_failure_before_success_seconds} />
                            <InputGroup.Append className={styles.inputGroupAppend}>
                              <InputGroup.Text className={postponedFailureTextClassName}>
                                { pluralize('seconds', values.postponed_failure_before_success_seconds ?? 0) }
                              </InputGroup.Text>
                            </InputGroup.Append>
                          </InputGroup>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormControl.Feedback type="invalid">
                            {errors.postponed_failure_before_success_seconds}
                          </FormControl.Feedback>
                        </Col>
                      </Row>
                    </FormGroup>
                    <FormGroup>
                      <Row className="mt-2 mb-2">
                        <Col>
                          <FormLabel className={postponedFailureTextClassName}>until</FormLabel>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <InputGroup className={styles.inputGroupWithUnit}>
                            <FormControl type="number" name="max_postponed_failure_count"
                              value={values.max_postponed_failure_count ?? ''}
                              min="0" step="1" onChange={handleChange}
                              disabled={disabledFailureNotifications || immediateFailureNotifications || isSubmitting}
                              isInvalid={!!errors.max_postponed_failure_count} />
                            <InputGroup.Append className={styles.inputGroupAppend}>
                              <InputGroup.Text className={postponedFailureTextClassName}>
                                { pluralize('execution', values.max_postponed_failure_count ?? 0) }
                              </InputGroup.Text>
                            </InputGroup.Append>
                          </InputGroup>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormControl.Feedback type="invalid">
                            {errors.max_postponed_failure_count}
                          </FormControl.Feedback>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormLabel className={'post-input-label ' + postponedFailureTextClassName} >
                            { pluralize('has', values.max_postponed_failure_count ?? 0) } failed
                          </FormLabel>
                        </Col>
                      </Row>
                    </FormGroup>
                    <FormGroup>
                      <Row className="mb-2">
                        <Col>
                          <FormLabel className={postponedFailureTextClassName}>
                            Cancel postponed failure notifications when
                          </FormLabel>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <InputGroup className={styles.inputGroupWithUnit}>
                            <FormControl type="number" name="required_success_count_to_clear_failure"
                            value={values.required_success_count_to_clear_failure ?? 1}
                            min="1" step="1" onChange={handleChange}
                            disabled={disabledFailureNotifications || immediateFailureNotifications || isSubmitting}
                            isInvalid={!!errors.required_success_count_to_clear_failure} />
                            <InputGroup.Append className={styles.inputGroupAppend}>
                              <InputGroup.Text className={postponedFailureTextClassName}>
                                { pluralize('execution', values.required_success_count_to_clear_failure ?? 1) }
                              </InputGroup.Text>
                            </InputGroup.Append>
                          </InputGroup>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormControl.Feedback type="invalid">
                            {errors.required_success_count_to_clear_failure}
                          </FormControl.Feedback>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormLabel className={'post-input-label ' + postponedFailureTextClassName} >
                            {
                              ((values.required_success_count_to_clear_failure ?? 1) === 1) ?
                              'completes' : 'complete'
                            }
                            &nbsp;successfully
                          </FormLabel>
                        </Col>
                      </Row>
                    </FormGroup>
                  </fieldset>


                  <fieldset>
                    <Row>
                      <Col>
                        <legend>Timeout Notifications</legend>
                      </Col>
                    </Row>

                    <FormGroup>
                      <Row>
                        <Col sm={4} md={3} className={styles.labelColumn}>
                          <FormLabel>Severity level</FormLabel>
                        </Col>
                        <Col>
                          <NotificationEventSeveritySelector selectedSeverity={values.notification_event_severity_on_timeout}
                           onSelectedSeverityChanged={ (severity) =>
                            setFieldValue('notification_event_severity_on_timeout', severity)
                           }/>
                        </Col>
                      </Row>
                    </FormGroup>


                    <FormGroup>
                      <Row>
                        <Col>
                          <FormCheck id="immediate_timeout_notifications_checkbox"
                            type="radio" label="Send timeout notifications immediately"
                            disabled={isSubmitting || disabledTimeoutNotifications}
                            checked={immediateTimeoutNotifications}
                            onChange={disablePostponedTimeoutNotifications} />
                        </Col>
                      </Row>
                    </FormGroup>
                    <FormGroup>
                      <Row className="mb-3">
                        <Col>
                          <FormCheck id="postpone_timeout_notifications_checkbox"
                            type="radio" label="Postpone timeout notifications for"
                            disabled={isSubmitting || disabledTimeoutNotifications}
                            checked={!immediateTimeoutNotifications}
                            onChange={enablePostponedTimeoutNotifications}>
                          </FormCheck>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <InputGroup className={styles.inputGroupWithUnit}>
                            <FormControl type="number" name="postponed_timeout_before_success_seconds"
                              value={values.postponed_timeout_before_success_seconds ?? ''}
                              min="0" step="1" onChange={handleChange}
                              disabled={isSubmitting || disabledTimeoutNotifications || immediateTimeoutNotifications}
                              isInvalid={!!errors.postponed_timeout_before_success_seconds} />
                            <InputGroup.Append className={styles.inputGroupAppend}>
                              <InputGroup.Text className={postponedTimeoutTextClassName}>
                                { pluralize('seconds', values.postponed_timeout_before_success_seconds ?? 0) }
                              </InputGroup.Text>
                            </InputGroup.Append>
                          </InputGroup>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormControl.Feedback type="invalid">
                            {errors.postponed_timeout_before_success_seconds}
                          </FormControl.Feedback>
                        </Col>
                      </Row>
                    </FormGroup>
                    <FormGroup>
                      <Row className="mt-2 mb-2">
                        <Col>
                          <FormLabel className={postponedTimeoutTextClassName}>until</FormLabel>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <InputGroup className={styles.inputGroupWithUnit}>
                            <FormControl type="number" name="max_postponed_timeout_count"
                              value={values.max_postponed_timeout_count ?? ''}
                              min="0" step="1" onChange={handleChange}
                              disabled={isSubmitting || disabledTimeoutNotifications || immediateTimeoutNotifications}
                              isInvalid={!!errors.max_postponed_timeout_count} />
                            <InputGroup.Append className={styles.inputGroupAppend}>
                              <InputGroup.Text className={postponedTimeoutTextClassName}>
                                { pluralize('execution', values.max_postponed_timeout_count ?? 0) }
                              </InputGroup.Text>
                            </InputGroup.Append>
                          </InputGroup>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormControl.Feedback type="invalid">
                            {errors.max_postponed_timeout_count}
                          </FormControl.Feedback>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormLabel className={'post-input-label ' + postponedTimeoutTextClassName} >
                            { pluralize('has', values.max_postponed_timeout_count ?? 0) } timed out
                          </FormLabel>
                        </Col>
                      </Row>
                    </FormGroup>
                    <FormGroup>
                      <Row className="mb-2">
                        <Col>
                          <FormLabel className={postponedTimeoutTextClassName}>
                            Cancel postponed timeout notifications when
                          </FormLabel>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <InputGroup className={styles.inputGroupWithUnit}>
                            <FormControl type="number" name="required_success_count_to_clear_timeout"
                            value={'' + (values.required_success_count_to_clear_timeout ?? 1)}
                            min="1" step="1" onChange={handleChange}
                            disabled={isSubmitting || disabledTimeoutNotifications || immediateTimeoutNotifications}
                            isInvalid={!!errors.required_success_count_to_clear_timeout} />
                            <InputGroup.Append className={styles.inputGroupAppend}>
                              <InputGroup.Text className={postponedTimeoutTextClassName}>
                                { pluralize('execution', values.required_success_count_to_clear_timeout ?? 1) }
                              </InputGroup.Text>
                            </InputGroup.Append>
                          </InputGroup>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormControl.Feedback type="invalid">
                            {errors.required_success_count_to_clear_timeout}
                          </FormControl.Feedback>
                        </Col>
                      </Row>
                      <Row>
                        <Col>
                          <FormLabel className={'post-input-label ' + postponedTimeoutTextClassName} >
                            {
                              ((values.required_success_count_to_clear_timeout ?? 1) === 1) ?
                              'completes' : 'complete'
                            }
                            &nbsp;successfully
                          </FormLabel>
                        </Col>
                      </Row>
                    </FormGroup>
                  </fieldset>

                  <fieldset>
                    <legend>Other Notifications</legend>
                    <Row>
                      <Col>
                        <FormText>Select the severity level of notifications after:</FormText>
                      </Col>
                    </Row>
                    <FormGroup>
                      <Row>
                        <Col sm={4} md={3} className={styles.labelColumn}>
                          <FormLabel>Missing heartbeats</FormLabel>
                        </Col>
                        <Col>
                          <NotificationEventSeveritySelector selectedSeverity={values.notification_event_severity_on_missing_heartbeat}
                           onSelectedSeverityChanged={ (severity) => setFieldValue('notification_event_severity_on_missing_heartbeat', severity)
                           }/>
                        </Col>
                      </Row>
                    </FormGroup>
                    <FormGroup>
                      <Row>
                        <Col sm={4} md={3} className={styles.labelColumn}>
                          <FormLabel>Successful executions</FormLabel>
                        </Col>
                        <Col>
                          <NotificationEventSeveritySelector selectedSeverity={values.notification_event_severity_on_success}
                           onSelectedSeverityChanged={ (severity) => setFieldValue('notification_event_severity_on_success', severity)
                           }/>
                        </Col>
                      </Row>
                    </FormGroup>
                    <FormGroup>
                      <Row>
                        <Col sm={4} md={3} className={styles.labelColumn}>
                          <FormLabel>Missing scheduled executions</FormLabel>
                        </Col>
                        <Col>
                          <NotificationEventSeveritySelector selectedSeverity={values.notification_event_severity_on_missing_execution}
                           disabled={!task.schedule}
                           onSelectedSeverityChanged={ (severity) => setFieldValue('notification_event_severity_on_missing_execution', severity)
                           }/>
                        </Col>
                      </Row>
                    </FormGroup>
                    <FormGroup>
                      <Row>
                        <Col sm={4} md={3} className={styles.labelColumn}>
                          <FormLabel>Service down</FormLabel>
                        </Col>
                        <Col>
                          <NotificationEventSeveritySelector selectedSeverity={values.notification_event_severity_on_service_down}
                           disabled={!task.is_service}
                           onSelectedSeverityChanged={ (severity) => setFieldValue('notification_event_severity_on_service_down', severity)
                           }/>
                        </Col>
                      </Row>
                    </FormGroup>

                  </fieldset>


                  <fieldset>
                    <legend>Notification Methods</legend>
                    <Row>
                      <Col>
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
                      </Col>
                    </Row>
                  </fieldset>

                  <CustomButton className={styles.saveButton}
                    onActionRequested={ (action, cbData) => handleSubmit() }
                    color="primary"
                    type="button"
                    disabled={isSubmitting}
                    label="Save changes"
                    inProgress={isSubmitting}
                    faIconName="save"
                  />
                </Form>
              </div>
            </Fragment>
          );
        }
      }
      </Formik>
    </Container>
	);
}

export default TaskNotificationsTab;