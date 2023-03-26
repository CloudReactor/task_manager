import _ from 'lodash';

import { ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';

import { AlertMethod, makeNewAlertMethod } from '../../types/domain_types';
import {
  saveAlertMethod
} from '../../utils/api';

import * as Yup from 'yup';

import React, { useContext } from 'react';

import {
  Container,
  Col,
  Row,
  Form,
  FormCheck,
  FormText,
} from 'react-bootstrap/'

import {
  Formik,
  Form as FormikForm,
  FieldArray,
  Field,
  ErrorMessage
} from 'formik';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import '../Tasks/style.scss';

import { Button } from '@material-ui/core/';

import RunEnvironmentSelector from '../common/RunEnvironmentSelector';
import EmailNotificationProfileSelector from '../common/EmailNotificationProfileSelector';
import PagerDutyProfileSelector from '../common/PagerDutyProfileSelector';
import FormikErrorsSummary from '../common/FormikErrorsSummary';


type Props = {
  alertMethod?: AlertMethod;
  onSaveStarted?: () => void;
  onSaveSuccess?: (alertMethod: AlertMethod) => void;
  onSaveError?: (ex: Error, values: any) => void;
}

const validationSchema = Yup.object().shape({
  name: Yup.string().max(200).required(),
  description: Yup.string().max(5000),
  enabled: Yup.boolean(),
  notify_on_success: Yup.boolean(),
  notify_on_failure: Yup.boolean(),
  notify_on_timeout: Yup.boolean(),
  method_details: Yup.object().shape({
    type: Yup.string().required(),
    profile: Yup.object().shape({
      uuid: Yup.string().required()
    }).required()
  })
});

const AlertMethodEditor = ({
  alertMethod,
  onSaveStarted,
  onSaveSuccess,
  onSaveError
}: Props) => {
  const context = useContext(GlobalContext);

  const {
    currentGroup
  } = context

  const accessLevel = accessLevelForCurrentGroup(context);
  const isAccessAllowed = accessLevel && (accessLevel >= ACCESS_LEVEL_DEVELOPER);

  const am = alertMethod ?? makeNewAlertMethod();
  const initialValues = Object.assign({
    runEnvironmentUuid: am.run_environment?.uuid
  }, am) as any;

  return (
    <Container fluid={true}>
      <Formik
        initialValues={initialValues}
        enableReinitialize={true}
        validationSchema={validationSchema}
        onSubmit={async (values, actions) => {
          try {
            const v = Object.assign({}, values);

            if (!alertMethod && currentGroup) {
              v.created_by_group = { id: currentGroup.id };
            }

            v.run_environment = values.runEnvironmentUuid ? {
              uuid: values.runEnvironmentUuid
            } : null;

            delete v.runEnvironmentUuid;

            if (onSaveStarted) {
              onSaveStarted();
            }

            actions.setSubmitting(true);

            const uuid = am.uuid || 'new';
            const saved = await saveAlertMethod(uuid, v);

            actions.setSubmitting(false);

            if (onSaveSuccess) {
              onSaveSuccess(saved);
            }
          } catch (ex) {
            actions.setSubmitting(false);
            if (onSaveError) {
              onSaveError(ex, values);
            }
          }
        }}
      >
        {({
          handleSubmit,
          handleChange,
          values,
          errors,
          isValid,
          touched,
          isSubmitting,
          setFieldValue
        }) => (

          <FormikForm noValidate onSubmit={handleSubmit}>
            <fieldset disabled={!isAccessAllowed || isSubmitting}>
              <Row className="pb-3">
                <Col>
                  <FormikErrorsSummary errors={errors} touched={touched}
                    values={values}/>
                </Col>
              </Row>
              <Row className="pb-3">
                <Col sm={6} className="align-self-center">
                  Name
                </Col>
                <Col sm={6}>
                  <Field
                    type="text"
                    name="name"
                    placeholder="Give this Alert Method a name"
                    className="form-control"
                    required={true}
                  />
                  <ErrorMessage name="name" />
                </Col>
              </Row>

              <Row className="pb-3">
                <Col sm={6} className="align-self-center">
                  Description
                </Col>
                <Col sm={6}>
                  <Field
                    type="text"
                    name="description"
                    placeholder="Description of this Alert Method"
                    className="form-control"
                  />
                  <ErrorMessage name="description" />
                </Col>
              </Row>

              <Form.Group as={Row} controlId="run-environment-input">
                <Form.Label column sm={6}>
                  Run Environment
                </Form.Label>
                <Col sm={6}>
                  <RunEnvironmentSelector selectedUuid={values.runEnvironmentUuid}
                    groupId={currentGroup?.id}
                    onChange={(selectedUuid: string | null) => {
                      setFieldValue('runEnvironmentUuid', selectedUuid);
                    }} noSelectionText="Any" />

                  <Form.Text>
                    Select the Run Environment the Alert Method is for.
                    Tasks and Workflows scoped to different Run Environments won&apos;t
                    be able use this Alert Method. Set to <code>Any</code> if you want
                    any Task or Workflow in the Group to be able to use this
                    Alert Method.
                  </Form.Text>

                  <ErrorMessage name="groupId" />
                </Col>
              </Form.Group>

              <Row className="pb-3">
                <Col sm={6} className="align-self-center">
                  Enabled
                </Col>
                <Col sm={6}>
                  <FormCheck
                    aria-label="Enabled">
                    <Field as={FormCheck.Input} name="enabled" type="checkbox" isValid />
                    <FormCheck.Label></FormCheck.Label>
                  </FormCheck>
                  <FormText className="text-muted">
                    Uncheck to disable alerts from this Alert Method
                  </FormText>
                </Col>
              </Row>

              {
                ['success', 'failure', 'timeout'].map(eventType => (
                  <Row key={eventType} className="pb-3">
                    <Col sm={6} className="align-self-center">
                      Notify on {eventType}
                    </Col>
                    <Col sm={6}>
                      <FormCheck aria-label={'Notify on ' + eventType}>
                        <Field as={FormCheck.Input} name={'notify_on_' + eventType}
                          type="checkbox" isValid />
                      </FormCheck>
                    </Col>
                  </Row>
                ))
              }

              <Row className="pb-3">
                <Col sm={6} className="align-self-center">
                  Event severity on missing scheduled execution
                </Col>
                <Col sm={6}>

                  <Field
                    component="select"
                    name="error_severity_on_missing_execution"
                    className="form-control"
                    onChange={handleChange}
                  >
                    <option value="critical">Critical</option>
                    <option value="error">Error</option>
                    <option value="warning">Warning</option>
                    <option value="info">Info</option>
                    <option value="">None</option>
                  </Field>
                  <ErrorMessage name="error_severity_on_missing_execution" />
                </Col>
              </Row>

              <Row className="pb-3">
                <Col sm={6} className="align-self-center">
                  Event severity on missing heartbeat
                </Col>
                <Col sm={6}>

                  <Field
                    component="select"
                    name="error_severity_on_service_down"
                    className="form-control"
                    onChange={handleChange}
                  >
                    <option value="critical">Critical</option>
                    <option value="error">Error</option>
                    <option value="warning">Warning</option>
                    <option value="info">Info</option>
                    <option value="">None</option>
                  </Field>
                  <ErrorMessage name="error_severity_on_service_down" />
                </Col>
              </Row>

              <Row className="pb-3">
                <Col sm={6} className="align-self-center">
                  Event severity when a service is down
                </Col>
                <Col sm={6}>

                  <Field
                    component="select"
                    name="error_severity_on_missing_heartbeat"
                    className="form-control"
                    onChange={handleChange}
                  >
                    <option value="critical">Critical</option>
                    <option value="error">Error</option>
                    <option value="warning">Warning</option>
                    <option value="info">Info</option>
                    <option value="">None</option>
                  </Field>
                  <ErrorMessage name="error_severity_on_missing_heartbeat" />
                </Col>
              </Row>

              <Row className="pb-3">
                <Col sm={6} className="align-self-center">
                  Notification method
                </Col>
                <Col sm={6}>
                  <FormCheck type="radio" id="email_select" label="Email"
                    checked={values.method_details?.type === 'email'}
                    onChange={() => {
                      setFieldValue('method_details.type', 'email');
                      setFieldValue('method_details.profile.uuid', undefined);
                    }} />
                  <FormCheck type="radio" id="pagerduty_select" label="PagerDuty"
                    checked={values.method_details?.type === 'PagerDuty'}
                    onChange={() => {
                      setFieldValue('method_details.type', 'PagerDuty');
                      setFieldValue('method_details.profile.uuid', undefined);
                    }} />
                </Col>
              </Row>

              {

                (values.method_details?.type === 'email') ? (
                  <Row className="pb-3">
                    <Col sm={6} className="align-self-center">
                     Email Notification Profile
                    </Col>
                    <Col sm={6}>
                      <FieldArray
                        name="method_details.profile.uuid"
                        render={arrayHelpers => (
                            <EmailNotificationProfileSelector
                              selectedEmailNotificationProfile={_.get(values, 'method_details.profile.uuid')}
                              changedEmailNotificationProfile={(uuid: string) => {
                                setFieldValue('method_details.profile.uuid', uuid);
                              }}
                              runEnvironmentUuid={values.runEnvironmentUuid}
                            />
                          )
                        }
                      />
                    </Col>
                  </Row>
                ) : (
                  <Row className="pb-3">
                    <Col sm={6} className="align-self-center">
                      PagerDuty Profile
                    </Col>
                    <Col sm={6}>
                      <FieldArray
                        name="method_details.profile.uuid"
                        render={arrayHelpers => {
                          return (
                            <PagerDutyProfileSelector
                            selectedPagerDutyProfile={_.get(values, 'method_details.profile.uuid')}
                            changedPagerDutyProfile={(uuid: string) => {
                              setFieldValue('method_details.profile.uuid', uuid);
                            }}
                            runEnvironmentUuid={values.runEnvironmentUuid}
                            />
                          );
                        }}
                      />
                    </Col>
                  </Row>
                )
              }

              {
                isAccessAllowed && (
                  <Row className="pb-3">
                    <Col sm={6} className="align-self-center"/>
                    <Col sm={6}>
                      <Button variant="outlined" color="primary" size="large" type="submit"
                        disabled={isSubmitting || (Object.keys(errors).length > 0)}>Save</Button>
                    </Col>
                  </Row>
                )
              }
            </fieldset>
          </FormikForm>
        )}
      </Formik>
    </Container>
  );
}

export default AlertMethodEditor;