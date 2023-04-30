import { ApiKey } from '../../../types/domain_types';
import { saveApiKey, fetchApiKey, makeErrorElement } from '../../../utils/api';
import * as C from '../../../utils/constants';
import { catchableToString } from '../../../utils';

import * as Yup from 'yup';

import React, { Fragment, useContext, useEffect, useState } from "react";
import { Link, useHistory, useParams } from 'react-router-dom';

import { Alert, Row, Col, Form, FormCheck } from 'react-bootstrap/';

import { Formik, Form as FormikForm, Field, ErrorMessage } from 'formik';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import Loading from '../../../components/Loading';
import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import GroupSelector from '../../../components/common/GroupSelector';
import RunEnvironmentSelector from '../../../components/common/RunEnvironmentSelector';
import AccessLevelSelector from '../../../components/common/AccessLevelSelector';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';
import CustomButton from '../../../components/common/Button/CustomButton';
import styles from './ApiKeyEditor.module.scss';
import FormikErrorsSummary from '../../../components/common/FormikErrorsSummary';

type PathParamsType = {
  uuid: string;
};

type Props = AbortSignalProps;

interface State {
  apiKey: ApiKey | any;
  isLoading: boolean;
  errorComponent?: any;
  isSaving: boolean;
}

const validationSchema = Yup.object().shape({
  name: Yup.string().max(200),
  enabled: Yup.boolean(),
  groupId: Yup.number().required(),
  runEnvironmentUuid: Yup.string().nullable(),
  description: Yup.string().max(1000)
});

const ApiKeyEditor = ({
  abortSignal
}: Props) => {
  const {
    uuid
  } = useParams<PathParamsType>();

  const isNew = (uuid === 'new');

  const history = useHistory();

  const context = useContext(GlobalContext);

  const [apiKey, setApiKey] = useState<ApiKey | any>(null);
  const [isLoading, setLoading] = useState(false);
  const [isSaving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadApiKey = async () => {
    setLoading(true);
    try {
      const updatedApiKey = await fetchApiKey(uuid, abortSignal);
      setApiKey(updatedApiKey);
    } catch (err) {
      setErrorMessage("Failed to load API Key: "  + catchableToString(err));
    } finally {
      setLoading(false);
    }
  }

  const renderApiKeyForm = () => {
    const accessLevel = accessLevelForCurrentGroup(context);

    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return <p>You don&apos;t have permission to access this page.</p>;
    }

    const initialValues = {
      uuid: apiKey?.uuid,
      name: apiKey?.name,
      description: apiKey?.description,
      enabled: apiKey?.enabled ?? true,
      access_level: apiKey?.access_level ?? C.ACCESS_LEVEL_TASK,
      groupId: apiKey?.group?.id,
      runEnvironmentUuid: apiKey?.run_environment?.uuid
    };

    return (
      <Fragment>
        {
          errorMessage &&
          <Alert variant="danger">
            { errorMessage }
          </Alert>
        }

        <div className={styles.formContainer}>
          <Formik
            initialValues={initialValues}
            validationSchema={validationSchema}
            enableReinitialize={true}
            onSubmit={async (values, actions) => {
              setSaving(true);
              setErrorMessage(null);

              const apiKeyToSave = Object.assign({
                group: {
                  id: values.groupId
                }
              }, values);

              delete apiKeyToSave.groupId;

              if (values.runEnvironmentUuid) {
                apiKeyToSave['run_environment'] = {
                  uuid: values.runEnvironmentUuid
                };
                delete apiKeyToSave.runEnvironmentUuid;
              }

              try {
                await saveApiKey(apiKeyToSave);
                setErrorMessage(null);

                history.push('/api_keys/');
              } catch (err) {
                setErrorMessage("Failed to save API Key: "  + catchableToString(err));
              } finally {
                setSaving(false);
              }
            }}
          >
            {({
              handleSubmit,
              handleChange,
              values,
              errors,
              isValid,
              status,
              touched,
              isSubmitting,
              setFieldValue
            }) => (

              <FormikForm noValidate onSubmit={handleSubmit}>
                <FormikErrorsSummary errors={errors} touched={touched}
                 values={values} />

                <Form.Group as={Row} controlId="name-input">
                  <Form.Label column sm={3}>
                    Name
                  </Form.Label>
                  <Col>
                    <Field name="name" placeholder="Give this API key a name"
                     as={Form.Control} />
                  </Col>
                </Form.Group>

                <Form.Group as={Row} controlId="group-input">
                  <Form.Label column sm={3}>
                    Group
                  </Form.Label>
                  <Col>
                    <GroupSelector selectedGroupId={values.groupId as number}
                      onSelectedGroupIdChanged={(groupId?: number) => {
                        setFieldValue('groupId', groupId);
                        setFieldValue('runEnvironmentUuid', undefined);
                      }} disabled={ !isNew } />

                    <Form.Text>
                      {
                        isNew ?
                        <Fragment>Select the Group the API Key will have access to.</Fragment> :
                        <Fragment>The Group of an API Key can&apos;t be changed after creation.</Fragment>
                      }
                    </Form.Text>

                    <ErrorMessage name="groupId" />
                  </Col>
                </Form.Group>

                <Form.Group as={Row} controlId="run-environment-input">
                  <Form.Label column sm={3}>
                    Run Environment
                  </Form.Label>
                  <Col>
                    <RunEnvironmentSelector selectedUuid={values.runEnvironmentUuid}
                      groupId={values.groupId}
                      onChange={(selectedUuid: string | null) => {
                        setFieldValue('runEnvironmentUuid', selectedUuid);
                      }} noSelectionText="Any" />

                    <Form.Text>
                      Select the Run Environment the API key will have access to.
                      The API key will be only able to perform operations on Tasks and
                      Workflows in the selected group.
                      You may choose &quot;Any&quot; in which case the API key will have access
                      to all Tasks and Workflows in the selected Group above.
                    </Form.Text>

                    <ErrorMessage name="groupId" />
                  </Col>
                </Form.Group>

                <Row className="pb-3">
                  <Col sm={3} className="align-self-center">
                    Enabled
                  </Col>
                  <Col>
                    <FormCheck aria-label="Enabled" title="Uncheck to disable this API Key">
                      <Field as={FormCheck.Input} name="enabled" type="checkbox" isValid />
                      <FormCheck.Label></FormCheck.Label>
                    </FormCheck>
                  </Col>
                </Row>

                <Form.Group as={Row} controlId="input-access-leavel">
                  <Form.Label column sm={3}>
                    Access Level
                  </Form.Label>
                  <Col>
                    <Field name="access_level">
                      {
                        ({ field }) => (
                          <AccessLevelSelector maxAccessLevel={accessLevel}
                           {...field} />
                        )
                      }
                    </Field>
                  </Col>
                </Form.Group>

                <Form.Group as={Row} controlId="input-description">
                  <Form.Label column sm={3}>
                    Description
                  </Form.Label>
                  <Col>
                    <Field name="description">
                      {
                        ({ field }) => (
                          <Form.Control {...field} as="textarea" rows={3}
                           placeholder="(Optional) Describe what this API key is for"/>
                        )
                      }
                    </Field>
                  </Col>
                </Form.Group>

                <Form.Group as={Row}>
                  <Col sm={3} />
                  <Col>
                    <CustomButton
                      color="primary"
                      type="submit"
                      disabled={isSubmitting || (Object.keys(errors).length > 0)}
                      label="Save"
                    />
                  </Col>
                </Form.Group>
              </FormikForm>
            )}
          </Formik>
        </div>
      </Fragment>
    );
  }

  useEffect(() => {
    if (isNew) {
      // create ApiKey object matching form fields; Formik requires, even though inputs are empty
      setApiKey({});
    } else {
      // user is editing existing API Key
      loadApiKey();
    }
  }, []);

  const breadcrumbLink = isNew ? 'Create New' : (apiKey?.name || uuid);

  const ApiKeysLink = <Link to="/api_keys">API Keys</Link>

  return (
    <div className={styles.container}>
      <Row>
        <Col>
          <BreadcrumbBar
            firstLevel={ApiKeysLink}
            secondLevel={breadcrumbLink}
          />
        </Col>
      </Row>

      <Row>
        <Col>
          {
            isLoading ? (<Loading />) :
            renderApiKeyForm()
          }
        </Col>
      </Row>
    </div>
  );
}

export default abortableHoc(ApiKeyEditor);
