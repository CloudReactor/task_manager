import * as Yup from 'yup';

import { ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';

import {
  makeEmptyPagerDutyProfile,
  PagerDutyProfile
} from '../../types/domain_types';

import {
  savePagerDutyProfile
} from '../../utils/api';

import React, { useContext } from 'react';

import {
  ErrorMessage,
  Field,
  Form as FormikForm,
  Formik
} from 'formik';

import {
  Container,
  Col,
  Row,
  Form
} from 'react-bootstrap';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import FormikErrorsSummary from '../../components/common/FormikErrorsSummary';
import RunEnvironmentSelector from '../../components/common/RunEnvironmentSelector';

import { Button } from '@material-ui/core/';

import '../Tasks/style.scss';

type Props = {
  pagerDutyProfile?: PagerDutyProfile;
  onSaveStarted?: (pagerDutyProfile: PagerDutyProfile) => void;
  onSaveSuccess?: (pagerDutyProfile: PagerDutyProfile) => void;
  onSaveError?: (ex: unknown, values: any) => void;
}

const validationSchema = Yup.object().shape({
  name: Yup.string().max(200).required(),
  description: Yup.string().max(5000),
  integration_key: Yup.string().max(1000).required(),
  default_event_severity: Yup.string().max(10)
});

const PagerDutyProfileEditor = ({
  pagerDutyProfile,
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

  const pdp = pagerDutyProfile ?? makeEmptyPagerDutyProfile();
  const initialValues = Object.assign({
    runEnvironmentUuid: pdp.run_environment?.uuid
  }, pdp) as any;

  return (
    <Container fluid={true}>
      <Formik
        initialValues={initialValues}
        enableReinitialize={true}
        validationSchema={validationSchema}
        onSubmit={async (values, actions) => {
          try {
            const v = Object.assign({}, values);

            if (!pagerDutyProfile && currentGroup) {
              v.created_by_group = { id: currentGroup.id };
            }

            v.run_environment = values.runEnvironmentUuid ? {
              uuid: values.runEnvironmentUuid
            } : null;

            if (onSaveStarted) {
              onSaveStarted(values);
            }

            const uuid = pdp.uuid || 'new';
            const saved = await savePagerDutyProfile(uuid, v)

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
                    values={values} />
                </Col>
              </Row>
              <Row className="pb-3">
                <Col sm={12} md={3} className="align-self-center">
                  Name
                </Col>
                <Col sm={12} md={9}>
                  <Field
                    type="text"
                    name="name"
                    placeholder="Give this PagerDuty profile a name"
                    className="form-control"
                    required={true}
                  />
                  <ErrorMessage name="name" />
                </Col>
              </Row>

              <Row className="pb-3">
                <Col xs={12} md={3} className="align-self-center">
                  Description
                </Col>
                <Col sm={12} md={9}>
                  <Field
                    type="text"
                    name="description"
                    placeholder="Description of this PagerDuty Profile"
                    className="form-control"
                  />
                  <ErrorMessage name="description" />
                </Col>
              </Row>

              <Form.Group as={Row} controlId="run-environment-input">
                <Form.Label column sm={12} md={3}>
                  Run Environment
                </Form.Label>
                <Col sm={12} md={9}>
                  <RunEnvironmentSelector selectedUuid={values.runEnvironmentUuid}
                    groupId={currentGroup?.id}
                    onChange={(selectedUuid: string | null) => {
                      setFieldValue('runEnvironmentUuid', selectedUuid);
                    }} noSelectionText="Any" />

                  <Form.Text>
                    Select the Run Environment this Profile is for.
                    Notification Methods scoped to different Run Environments won&apos;t
                    be able use this Profile. Set to <code>Any</code> if you want
                    any Notification Method in the Group to be able to use this
                    Profile.
                  </Form.Text>

                  <ErrorMessage name="groupId" />
                </Col>
              </Form.Group>

              <Row className="pb-3">
                <Col sm={12} md={3} className="align-self-center">
                  Integration key
                </Col>
                <Col sm={12} md={9}>
                  <Field
                    type="text"
                    name="integration_key"
                    placeholder="PagerDuty API key"
                    className="form-control"
                    required={true}
                  />
                  <ErrorMessage name="integration_key" />
                </Col>
              </Row>

              <Row className="pb-3">
                <Col sm={12} md={3} className="align-self-center">
                  Default event severity
                </Col>
                <Col sm={12} md={9}>
                  <Field
                    component="select"
                    name="default_event_severity"
                    className="form-control"
                  >
                    <option value="critical">Critical</option>
                    <option value="error">Error</option>
                    <option value="warning">Warning</option>
                    <option value="info">Info</option>
                  </Field>
                  <ErrorMessage name="default_event_severity" />
                </Col>
              </Row>
              {
                isAccessAllowed && (
                  <Row className="pb-3">
                    <Col sm={12} md={3} className="align-self-center"/>
                    <Col sm={12} md={9}>
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

export default PagerDutyProfileEditor;
