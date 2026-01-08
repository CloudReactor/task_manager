import _ from 'lodash';

import { ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';

import {
  NotificationDeliveryMethod,
  EmailNotificationDeliveryMethod,
  PagerDutyNotificationDeliveryMethod,
  makeEmptyNotificationDeliveryMethod
} from '../../types/domain_types';
import {
  saveNotificationDeliveryMethod
} from '../../utils/api';

import * as Yup from 'yup';

import React, { useContext, useState, useEffect } from 'react';

import './NotificationDeliveryMethodEditor.css';

import {
  Container,
  Col,
  Row,
  Form
} from 'react-bootstrap/';

import {
  Formik,
  Form as FormikForm,
  Field,
  FieldArray,
  ErrorMessage
} from 'formik';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import { Button } from '@mui/material/';

import RunEnvironmentSelector from '../common/RunEnvironmentSelector';
import FormikErrorsSummary from '../common/FormikErrorsSummary';

type Props = {
  notificationDeliveryMethod?: NotificationDeliveryMethod;
  onSaveStarted?: (method: NotificationDeliveryMethod) => void;
  onSaveSuccess?: (method: NotificationDeliveryMethod) => void;
  onSaveError?: (err: unknown, values: any) => void;
}

const validationSchema = Yup.object().shape({
  name: Yup.string().max(200).required('Name is required'),
  description: Yup.string().max(5000),
  enabled: Yup.boolean(),
  delivery_method_type: Yup.string().oneOf(['email', 'pagerduty']).required('Type is required')
});

const emailValidationSchema = validationSchema.concat(Yup.object().shape({
  email_to_addresses: Yup.array().of(Yup.string().email()).min(1, 'At least one email address is required')
}));

const pagerdutyValidationSchema = validationSchema.concat(Yup.object().shape({
  pagerduty_api_key: Yup.string().required('API key is required')
}));

const NotificationDeliveryMethodEditor = ({
  notificationDeliveryMethod,
  onSaveStarted,
  onSaveSuccess,
  onSaveError
}: Props) => {
  const context = useContext(GlobalContext);

  const {
    currentGroup
  } = context;

  const accessLevel = accessLevelForCurrentGroup(context);
  const isAccessAllowed = accessLevel && (accessLevel >= ACCESS_LEVEL_DEVELOPER);

  // Helper to convert backend type to UI type
  const backendToUiType = (backendType?: string): string => {
    if (!backendType) return 'email';
    // Backend now returns "email" or "pager_duty"
    if (backendType === 'email') return 'email';
    if (backendType === 'pager_duty') return 'pagerduty';
    return backendType;
  };

  // Helper to convert UI type to backend type
  const uiToBackendType = (uiType: string): string => {
    // Backend expects "email" or "pager_duty"
    if (uiType === 'email') return 'email';
    if (uiType === 'pagerduty') return 'pager_duty';
    return uiType;
  };

  const method = notificationDeliveryMethod ?? makeEmptyNotificationDeliveryMethod();
  const methodType = backendToUiType(notificationDeliveryMethod?.delivery_method_type);

  const [selectedType, setSelectedType] = useState(methodType);

  // Cast to appropriate type based on delivery method type
  const emailMethod = method as EmailNotificationDeliveryMethod;
  const pagerdutyMethod = method as PagerDutyNotificationDeliveryMethod;

  const initialValues = Object.assign({}, method, {
    runEnvironmentUuid: method.run_environment?.uuid,
    delivery_method_type: selectedType, // Use selectedType state instead of methodType
    enabled: method.enabled !== false, // default to true
    email_to_addresses: emailMethod.email_to_addresses || [],
    email_cc_addresses: emailMethod.email_cc_addresses || [],
    email_bcc_addresses: emailMethod.email_bcc_addresses || [],
    pagerduty_api_key: pagerdutyMethod.pagerduty_api_key || ''
  }) as any;

  const getCurrentValidationSchema = () => {
    if (selectedType === 'email') {
      return emailValidationSchema;
    } else if (selectedType === 'pagerduty') {
      return pagerdutyValidationSchema;
    }
    return validationSchema;
  };

  return (
    <Container fluid={true}>
      <Formik
        initialValues={initialValues}
        enableReinitialize={true}
        validationSchema={getCurrentValidationSchema()}
        onSubmit={async (values, actions) => {
          try {
            const v = Object.assign({}, values);

            if (!notificationDeliveryMethod && currentGroup) {
              v.created_by_group = { id: currentGroup.id };
            }

            v.run_environment = (values.runEnvironmentUuid && values.runEnvironmentUuid !== '') ? {
              uuid: values.runEnvironmentUuid
            } : null;

            delete v.runEnvironmentUuid;

            // Convert UI type to backend type
            v.delivery_method_type = uiToBackendType(v.delivery_method_type);

            if (onSaveStarted) {
              onSaveStarted(values);
            }

            actions.setSubmitting(true);

            const uuid = method.uuid || 'new';
            const saved = await saveNotificationDeliveryMethod(uuid, v);

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

              {/* Basic Information */}
              <Row className="pb-3">
                <Col sm={6}>
                  <Form.Group controlId="name">
                    <Form.Label>Name *</Form.Label>
                    <Field
                      name="name"
                      type="text"
                      className="form-control"
                      placeholder="Enter notification method name"
                    />
                    <ErrorMessage name="name" component="div" className="text-danger" />
                  </Form.Group>
                </Col>
              </Row>

              <Row className="pb-3">
                <Col sm={12}>
                  <Form.Group controlId="description">
                    <Form.Label>Description</Form.Label>
                    <Field
                      name="description"
                      as="textarea"
                      rows={3}
                      className="form-control"
                      placeholder="Enter description (optional)"
                    />
                    <ErrorMessage name="description" component="div" className="text-danger" />
                  </Form.Group>
                </Col>
              </Row>

              <Row className="pb-3">
                <Col sm={6}>
                  <Form.Group controlId="runEnvironmentUuid">
                    <Form.Label>Run Environment</Form.Label>
                    <RunEnvironmentSelector
                      selectedUuid={values.runEnvironmentUuid}
                      onChange={(uuid) => {
                        setFieldValue('runEnvironmentUuid', uuid);
                      }}
                      groupId={currentGroup?.id}
                      noSelectionText="(Unscoped)"
                    />
                  </Form.Group>
                </Col>
              </Row>

              <Row className="pb-3">
                <Col sm={6}>
                  <Form.Group controlId="enabled">
                    <Form.Check
                      type="checkbox"
                      name="enabled"
                      label="Enabled"
                      checked={values.enabled}
                      onChange={handleChange}
                    />
                  </Form.Group>
                </Col>
              </Row>

              {/* Type Selector */}
              <Row className="pb-3">
                <Col sm={4} md={3}>
                  <Form.Group controlId="delivery_method_type">
                    <Form.Label>Delivery Method Type *</Form.Label>
                    { notificationDeliveryMethod ? (
                      <div
                        className="form-control"
                        style={{
                          backgroundColor: '#5d646b',
                          color: '#ffffff',
                          cursor: 'not-allowed'
                        }}
                      >
                        {selectedType === 'email' ? 'Email' : 'PagerDuty'}
                      </div>
                    ) : (
                      <Field
                        as="select"
                        name="delivery_method_type"
                        className="form-control"
                        value={values.delivery_method_type}
                        onChange={(e: any) => {
                          const newType = e.target.value;
                          setSelectedType(newType);
                          setFieldValue('delivery_method_type', newType);

                          // Reset type-specific fields
                          if (newType === 'email') {
                            setFieldValue('email_to_addresses', []);
                            setFieldValue('email_cc_addresses', []);
                            setFieldValue('email_bcc_addresses', []);
                          } else if (newType === 'pagerduty') {
                            setFieldValue('pagerduty_api_key', '');
                          }
                        }}
                      >
                        <option value="email">Email</option>
                        <option value="pagerduty">PagerDuty</option>
                      </Field>
                    )}
                    <ErrorMessage name="delivery_method_type" component="div" className="text-danger" />
                    {notificationDeliveryMethod && (
                      <Form.Text className="text-muted">
                        Type cannot be changed after creation
                      </Form.Text>
                    )}
                  </Form.Group>
                </Col>
              </Row>

              {/* Email-specific fields */}
              {selectedType === 'email' && (
                <>
                  <Row className="pb-3">
                    <Col sm={12}>
                      <Form.Group>
                        <Form.Label>To Addresses *</Form.Label>
                        <FieldArray name="email_to_addresses">
                          {({ push, remove }) => (
                            <>
                              {(values.email_to_addresses || []).length === 0 ? (
                                <div className="text-muted mb-2">No email addresses added yet.</div>
                              ) : (
                                (values.email_to_addresses || []).map((email: string, index: number) => (
                                  <div key={index} className="d-flex mb-2">
                                    <Field
                                      name={`email_to_addresses.${index}`}
                                      type="email"
                                      className="form-control"
                                      placeholder="email@example.com"
                                    />
                                    <button
                                      type="button"
                                      className="btn btn-danger ms-2"
                                      style={{ height: '50px' }}
                                      onClick={() => remove(index)}
                                    >
                                      <i className="fas fa-trash" />
                                    </button>
                                  </div>
                                ))
                              )}
                              <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => push('')}
                              >
                                <i className="fa fa-plus" /> Add Email Address
                              </button>
                              <ErrorMessage name="email_to_addresses" component="div" className="text-danger" />
                            </>
                          )}
                        </FieldArray>
                      </Form.Group>
                    </Col>
                  </Row>

                  <Row className="pb-3">
                    <Col sm={12}>
                      <Form.Group>
                        <Form.Label>CC Addresses</Form.Label>
                        <FieldArray name="email_cc_addresses">
                          {({ push, remove }) => (
                            <>
                              {(values.email_cc_addresses || []).length === 0 ? (
                                <div className="text-muted mb-2">No email addresses added yet.</div>
                              ) : (
                                (values.email_cc_addresses || []).map((email: string, index: number) => (
                                  <div key={index} className="d-flex mb-2">
                                    <Field
                                      name={`email_cc_addresses.${index}`}
                                      type="email"
                                      className="form-control"
                                      placeholder="email@example.com"
                                    />
                                    <button
                                      type="button"
                                      className="btn btn-danger ms-2"
                                      style={{ height: '50px' }}
                                      onClick={() => remove(index)}
                                    >
                                      <i className="fas fa-trash" />
                                    </button>
                                  </div>
                                ))
                              )}
                              <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => push('')}
                              >
                                <i className="fa fa-plus" /> Add Email Address
                              </button>
                              <ErrorMessage name="email_cc_addresses" component="div" className="text-danger" />
                            </>
                          )}
                        </FieldArray>
                      </Form.Group>
                    </Col>
                  </Row>

                  <Row className="pb-3">
                    <Col sm={12}>
                      <Form.Group>
                        <Form.Label>BCC Addresses</Form.Label>
                        <FieldArray name="email_bcc_addresses">
                          {({ push, remove }) => (
                            <>
                              {(values.email_bcc_addresses || []).length === 0 ? (
                                <div className="text-muted mb-2">No email addresses added yet.</div>
                              ) : (
                                (values.email_bcc_addresses || []).map((email: string, index: number) => (
                                  <div key={index} className="d-flex mb-2">
                                    <Field
                                      name={`email_bcc_addresses.${index}`}
                                      type="email"
                                      className="form-control"
                                      placeholder="email@example.com"
                                    />
                                    <button
                                      type="button"
                                      className="btn btn-danger ms-2"
                                      style={{ height: '50px' }}
                                      onClick={() => remove(index)}
                                    >
                                      <i className="fas fa-trash" />
                                    </button>
                                  </div>
                                ))
                              )}
                              <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => push('')}
                              >
                                <i className="fa fa-plus" /> Add Email Address
                              </button>
                              <ErrorMessage name="email_bcc_addresses" component="div" className="text-danger" />
                            </>
                          )}
                        </FieldArray>
                      </Form.Group>
                    </Col>
                  </Row>
                </>
              )}

              {/* PagerDuty-specific fields */}
              {selectedType === 'pagerduty' && (
                <>
                  <Row className="pb-3">
                    <Col sm={12}>
                      <Form.Group controlId="pagerduty_api_key">
                        <Form.Label>PagerDuty API Key *</Form.Label>
                        <Field
                          name="pagerduty_api_key"
                          type="text"
                          className="form-control"
                          placeholder="Enter PagerDuty API key"
                        />
                        <ErrorMessage name="pagerduty_api_key" component="div" className="text-danger" />
                      </Form.Group>
                    </Col>
                  </Row>
                </>
              )}

              {/* Submit Button */}
              <Row className="pt-4">
                <Col>
                  <Button
                    color="primary"
                    variant="contained"
                    type="submit"
                    disabled={!isAccessAllowed || isSubmitting || !isValid}
                  >
                    {isSubmitting ? 'Saving...' : 'Save'}
                  </Button>
                </Col>
              </Row>
            </fieldset>
          </FormikForm>
        )}
      </Formik>
    </Container>
  );
};

export default NotificationDeliveryMethodEditor;
