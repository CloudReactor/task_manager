import _ from 'lodash';

import { ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';

import {
  NotificationProfile,
  makeEmptyNotificationProfile
} from '../../types/domain_types';
import {
  saveNotificationProfile
} from '../../utils/api';

import * as Yup from 'yup';

import React, { useContext } from 'react';

import {
  Container,
  Col,
  Row,
  Form
} from 'react-bootstrap/';

import {
  Formik,
  Form as FormikForm,
  Field
} from 'formik';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import { Button } from '@mui/material/';

import RunEnvironmentSelector from '../common/RunEnvironmentSelector';
import NotificationDeliveryMethodSelector from '../common/NotificationDeliveryMethodSelector';
import FormikErrorsSummary from '../common/FormikErrorsSummary';

type Props = {
  notificationProfile?: NotificationProfile;
  onSaveStarted?: (profile: NotificationProfile) => void;
  onSaveSuccess?: (profile: NotificationProfile) => void;
  onSaveError?: (err: unknown, values: any) => void;
}

const validationSchema = Yup.object().shape({
  name: Yup.string().max(200).required('Name is required'),
  description: Yup.string().max(5000),
  enabled: Yup.boolean(),
  notification_delivery_methods: Yup.array()
});

const NotificationProfileEditor = ({
  notificationProfile,
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

  const profile = notificationProfile ?? makeEmptyNotificationProfile();

  const initialValues = Object.assign({}, profile, {
    runEnvironmentUuid: profile.run_environment?.uuid,
    enabled: profile.enabled !== false, // default to true
    notification_delivery_methods: profile.notification_delivery_methods || []
  }) as any;

  return (
    <Container fluid={true}>
      <Formik
        initialValues={initialValues}
        enableReinitialize={true}
        validationSchema={validationSchema}
        onSubmit={async (values, actions) => {
          try {
            const v = Object.assign({}, values);

            if (!notificationProfile && currentGroup) {
              v.created_by_group = { id: currentGroup.id };
            }

            v.run_environment = (values.runEnvironmentUuid && values.runEnvironmentUuid !== '') ? {
              uuid: values.runEnvironmentUuid
            } : null;

            delete v.runEnvironmentUuid;

            // Convert notification_delivery_methods array to array of references
            v.notification_delivery_methods = values.notification_delivery_methods.map((method: any) => {
              return method.uuid ? { uuid: method.uuid } : method;
            });

            if (onSaveStarted) {
              onSaveStarted(values);
            }

            actions.setSubmitting(true);

            const uuid = profile.uuid || 'new';
            const saved = await saveNotificationProfile(uuid, v);

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
                <Col>
                  <Form.Group controlId="name">
                    <Form.Label>Name *</Form.Label>
                    <Field
                      name="name"
                      type="text"
                      className="form-control"
                      placeholder="Enter name"
                    />
                    {touched.name && errors.name && (
                      <Form.Text className="text-danger">
                        {String(errors.name)}
                      </Form.Text>
                    )}
                  </Form.Group>
                </Col>
              </Row>

              <Row className="pb-3">
                <Col>
                  <Form.Group controlId="description">
                    <Form.Label>Description</Form.Label>
                    <Field
                      name="description"
                      as="textarea"
                      rows={3}
                      className="form-control"
                      placeholder="Enter description (optional)"
                    />
                    {touched.description && errors.description && (
                      <Form.Text className="text-danger">
                        {String(errors.description)}
                      </Form.Text>
                    )}
                  </Form.Group>
                </Col>
              </Row>

              <Row className="pb-3">
                <Col>
                  <Form.Group controlId="runEnvironmentUuid">
                    <Form.Label>Run Environment</Form.Label>
                    <RunEnvironmentSelector
                      selectedUuid={values.runEnvironmentUuid}
                      noSelectionText="Unscoped"
                      onChange={(runEnvironmentUuid: string | null) => {
                        setFieldValue('runEnvironmentUuid', runEnvironmentUuid);
                        // Clear selected delivery methods when run environment changes
                        // as they may no longer be compatible
                        setFieldValue('notification_delivery_methods', []);
                      }}
                    />
                    <Form.Text className="text-muted">
                      Optional. If set, only Notification Delivery Methods scoped to this Run Environment
                      or unscoped methods can be selected. If not set, any Notification Delivery Method
                      in your group can be selected.
                    </Form.Text>
                  </Form.Group>
                </Col>
              </Row>

              <Row className="pb-3">
                <Col>
                  <Form.Group controlId="enabled">
                    <Field name="enabled">
                      {({ field }: any) => (
                        <Form.Check
                          {...field}
                          type="checkbox"
                          checked={field.value}
                          label="Enable this Notification Profile"
                        />
                      )}
                    </Field>
                  </Form.Group>
                </Col>
              </Row>

              <Row className="pb-3">
                <Col>
                  <Form.Group controlId="notification_delivery_methods">
                    <Form.Label>Notification Delivery Methods *</Form.Label>
                    <NotificationDeliveryMethodSelector
                      entityTypeLabel="Notification Profile"
                      runEnvironmentUuid={values.runEnvironmentUuid}
                      selectedNotificationDeliveryMethodUuids={
                        values.notification_delivery_methods.map((method: any) => method.uuid)
                      }
                      onSelectedNotificationDeliveryMethodsChanged={(methods) => {
                        setFieldValue('notification_delivery_methods', methods);
                      }}
                    />
                    {touched.notification_delivery_methods && errors.notification_delivery_methods && (
                      <Form.Text className="text-danger">
                        {String(errors.notification_delivery_methods)}
                      </Form.Text>
                    )}
                    <Form.Text className="text-muted">
                      Select one or more Notification Delivery Methods to use for sending notifications.
                    </Form.Text>
                  </Form.Group>
                </Col>
              </Row>

              <Row className="pb-3">
                <Col>
                  <Button
                    type="submit"
                    variant="contained"
                    color="primary"
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
}

export default NotificationProfileEditor;
