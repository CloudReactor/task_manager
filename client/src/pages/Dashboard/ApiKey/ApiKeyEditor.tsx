import { ApiKey } from '../../../types/domain_types';
import { saveApiKey, fetchApiKey, makeErrorElement } from '../../../utils/api';
import * as C from '../../../utils/constants';

import * as Yup from 'yup';

import React, { Component, Fragment } from "react";
import { withRouter, RouteComponentProps } from "react-router";
import { Link } from 'react-router-dom';

import { Alert, Row, Col, Form, FormCheck } from 'react-bootstrap/';

import { Formik, Form as FormikForm, Field, ErrorMessage } from 'formik';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import GroupSelector from '../../../components/common/GroupSelector';
import RunEnvironmentSelector from '../../../components/common/RunEnvironmentSelector';
import AccessLevelSelector from '../../../components/common/AccessLevelSelector';
import CustomButton from '../../../components/common/Button/CustomButton';
import styles from './ApiKeyEditor.module.scss';
import FormikErrorsSummary from '../../../components/common/FormikErrorsSummary';

type PathParamsType = {
  uuid: string;
};

type Props = RouteComponentProps<PathParamsType>;

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
  runEnvironmentUuid: Yup.string(),
  description: Yup.string().max(1000)
});

class ApiKeyEditor extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    this.state = {
      apiKey: null,
      isLoading: false,
      isSaving: false
    };
  }

  componentDidMount() {
    const uuid = this.props.match.params.uuid;

    if (uuid === 'new') {
      // create ApiKey object matching form fields; Formik requires, even though inputs are empty
      this.setState({
        apiKey: {}
      })
    } else {
      // user is editing existing API Key
      this.fetchApiKey(uuid);
    }
  }

  async fetchApiKey(uuid: string) {
    this.setState({
      isLoading: true
    });
    try {
      const apiKey = await fetchApiKey(uuid);
      this.setState({
        apiKey,
        isLoading: false
      });
    } catch (ex: unknown) {
      let msg = '';

      if (typeof(ex) === 'string') {
        msg = ex;
      } else if (ex instanceof Error) {
        msg = ex.message;
      }

      this.setState({
        errorComponent: <div>Failed to load API Key: ${msg}</div>,
        isLoading: false
      });
    }
  }

  renderApiKeyForm() {
    const uuid = this.props.match.params.uuid;
    const isNew = (uuid === 'new');

    const {
      apiKey,
      errorComponent
    } = this.state;

    const accessLevel = accessLevelForCurrentGroup(this.context);

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
          errorComponent &&
          <Alert variant="danger">
            { errorComponent }
          </Alert>
        }

        <div className={styles.formContainer}>
          <Formik
            initialValues={initialValues}
            validationSchema={validationSchema}
            enableReinitialize={true}
            onSubmit={async (values, actions) => {

              this.setState({
                isSaving: true,
                errorComponent: undefined
              });

              const apiKey = Object.assign({
                group: {
                  id: values.groupId
                }
              }, values);

              delete apiKey.groupId;

              if (values.runEnvironmentUuid) {
                apiKey['run_environment'] = {
                  uuid: values.runEnvironmentUuid
                };
                delete apiKey.runEnvironmentUuid;
              }

              try {
                await saveApiKey(apiKey);
                this.setState({
                  errorComponent: undefined,
                  isSaving: false
                });

                this.props.history.push('/api_keys/');
              } catch (ex) {
                this.setState({
                  errorComponent: makeErrorElement(ex),
                  isSaving: false
                });
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

  public render() {
    const {
      apiKey
    } = this.state;

    const breadcrumbLink = this.props.match.params.uuid === 'new' ?
      'Create New' : (apiKey?.name || this.props.match.params.uuid);

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
              this.state.isLoading ? (<div>Loading ...</div>) :
              this.renderApiKeyForm()
            }
          </Col>
        </Row>
      </div>
    );
  }
}

export default withRouter(ApiKeyEditor);
