import * as Yup from 'yup';

import { ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';

import {
  makeEmptyEmailNotificationProfile,
  EmailNotificationProfile
} from '../../types/domain_types';

import {
  saveEmailNotificationProfile
} from '../../utils/api';

import React, { Fragment, useContext } from 'react';
import {
  ErrorMessage,
  Field,
  FieldArray,
  Form as FormikForm,
  Formik,
} from 'formik';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import { BootstrapVariant } from '../../types/ui_types';

import Container from '../Container/Container';
import CustomButton from '../common/Button/CustomButton';
import CustomInput from '../forms/CustomInput';
import styles from './EmailNotificationProfileEditor.module.scss';

import {
  Col,
  Row,
  InputGroup,
  Form,
  FormGroup,
  FormLabel,
} from 'react-bootstrap';

import { Button } from '@material-ui/core/';
import AddBoxIcon from '@material-ui/icons/AddBox';
import DeleteIcon from '@material-ui/icons/Delete';
import IconButton from '@material-ui/core/IconButton';

import RunEnvironmentSelector from '../common/RunEnvironmentSelector';
import FormikErrorsSummary from '../common/FormikErrorsSummary';

import '../Tasks/style.scss';

type Props = {
  emailNotificationProfile?: EmailNotificationProfile;
  onSaveStarted?: () => void;
  onSaveSuccess?: (enp: EmailNotificationProfile) => void;
  onSaveError?: (ex: Error, values: any) => void;
}

interface State {
  emailNotificationProfile: EmailNotificationProfile | any;
  isLoading: boolean;
  isSaving: boolean;
  flashBody?: any;
  flashAlertVariant?: BootstrapVariant;
}

const validationSchema = Yup.object().shape({
  name: Yup.string().max(200)
    .required(),
  description: Yup.string().max(5000),
  to_addresses: Yup.array(),
  cc_addresses: Yup.array(),
  bcc_addresses: Yup.array(),
  subject_template: Yup.string().max(1000),
  body_template: Yup.string().max(1000)
});

const leftIcon = {
  marginRight: '8px',
};

const EmailNotificationProfileEditor = ({
  emailNotificationProfile,
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
  const enp = emailNotificationProfile ||  makeEmptyEmailNotificationProfile();
  const initialValues = Object.assign({
    runEnvironmentUuid: enp.run_environment?.uuid
  }, enp) as any;

  return (
    <Container type="formContainer">
      <Formik
        initialValues={initialValues}
        enableReinitialize={true}
        validationSchema={validationSchema}
        onSubmit={async (values, actions) => {
          try {
            const v = Object.assign({}, values);

            if (!emailNotificationProfile && currentGroup) {
              v.created_by_group = { id: currentGroup?.id };
            }

            v.run_environment = values.runEnvironmentUuid ? {
              uuid: values.runEnvironmentUuid
            } : null;

            if (onSaveStarted) {
              onSaveStarted();
            }

            actions.setSubmitting(true);

            const uuid = enp.uuid || 'new';
            const saved = await saveEmailNotificationProfile(uuid, v);

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
          touched,
          isValid,
          isSubmitting,
          setFieldValue
        }) => (

          <FormikForm noValidate onSubmit={handleSubmit}>
            <FormikErrorsSummary errors={errors} touched={touched}
              values={values} />

            <div className={styles.formSection}>
              <div className={styles.sectionTitle}>General</div>
              <Form.Group as={Row}>
                <Form.Label column sm={12} md={3}>
                  Name
                </Form.Label>

                <Col sm={12} md={9}>
                  <Field name="name" controlId="forName"
                    placeholder="Give this Email Notification profile a name"
                    component={CustomInput} omitLabel={true}
                    onChange={handleChange} />
                </Col>
              </Form.Group>

              <Form.Group as={Row}>
                <Form.Label column xs={12} md={3}>
                  Description
                </Form.Label>

                <Col xs={12} md={9}>
                  <Field name="description" controlId="forDescription"
                    placeholder="Description of this Profile"
                    component={CustomInput} omitLabel={true}
                    onChange={handleChange} />
                </Col>
              </Form.Group>

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
                    Alert Methods scoped to different Run Environments won't
                    be able use this Profile. Set to <code>Any</code> if you want
                    any Alert Method in the Group to be able to use this
                    Profile.
                  </Form.Text>

                  <ErrorMessage name="groupId" />
                </Col>
              </Form.Group>
            </div>

            <div className={styles.formSection}>
              <div className={styles.sectionTitle}>Recipients</div>
              <FormGroup controlId="forRecipients">
                <FormLabel>Define email recipients for this Profile</FormLabel>
              </FormGroup>
              {
                ['to', 'cc', 'bcc'].map(rt => {
                  const isTo = (rt === 'to');
                  const upperRt = rt.toUpperCase();
                  const rtLabel = isTo ? 'To' : upperRt;
                  const addresses = values[rt + '_addresses'];

                  return (
                  <Row key={rt} className="pb-3">
                    <Col sm={12} md={3} className="align-text-top">
                      <label>{rtLabel} Email Addresses</label>
                    </Col>

                    <Col sm={12} md={9}>
                      <FieldArray
                        name={rt + '_addresses'}
                        render={(arrayHelpers: any) => (
                          <Fragment>
                            {addresses && addresses.length > 0 ? (
                            addresses.map((item: any, index: any) => (
                                <InputGroup key={index} className="mb-3">
                                  <Field name={`${rt}_addresses.${index}`} type="text"
                                  className="form-control"/>
                                  <InputGroup.Append>
                                    <IconButton
                                      aria-label="delete"
                                      onClick={() => arrayHelpers.remove(index)}
                                  >
                                      <DeleteIcon />
                                    </IconButton>
                                  </InputGroup.Append>
                                </InputGroup>
                              ))
                            ) : null }
                            <Button variant="outlined" size="small" onClick={() => arrayHelpers.push('')}>
                              <AddBoxIcon style={leftIcon} />
                              Add email address
                            </Button>
                          </Fragment>
                        )}
                      />
                    </Col>
                  </Row>);
                })
              }
            </div>
            {
              isAccessAllowed && (
                <CustomButton
                  color="primary"
                  className={styles.saveButton}
                  type="submit"
                  disabled={isSubmitting}
                  label="Save"
                />
              )
            }
          </FormikForm>

        )}
      </Formik>
    </Container>
  );
}

export default EmailNotificationProfileEditor;
