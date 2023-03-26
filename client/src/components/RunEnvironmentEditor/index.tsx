import {
  ACCESS_LEVEL_DEVELOPER,
  EXECUTION_METHOD_TYPE_AWS_ECS
} from '../../utils/constants';

import {
  AlertMethod,
  RunEnvironment,
  makeNewRunEnvironment
} from '../../types/domain_types';

import {
  saveRunEnvironment
} from '../../utils/api';

import * as Yup from 'yup';

import React, { useContext, useState, Fragment } from 'react';

import {
  Col,
  Row,
  FormCheck,
  FormGroup,
  FormLabel,
  InputGroup,
} from 'react-bootstrap';

import { Formik, Form, FieldArray, Field, ErrorMessage } from 'formik';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import { Button } from '@material-ui/core/';
import AddBoxIcon from '@material-ui/icons/AddBox';
import DeleteIcon from '@material-ui/icons/Delete';
import IconButton from '@material-ui/core/IconButton';

import FormikErrorsSummary from '../common/FormikErrorsSummary';

import AlertMethodSelector from '../common/AlertMethodSelector';

import commonItems from './RunEnvironmentEditorCommonItems.js';
import items1 from './RunEnvironmentEditorItems-1.js';
import items2 from './RunEnvironmentEditorItems-2.js';
import SettingsForm from '../../components/forms/SettingsForm';
import styles from './index.module.scss';


type Props = {
  runEnvironment?: RunEnvironment;
  onSaveStarted?: () => void;
  onSaveSuccess?: (runEnvironment: RunEnvironment) => void;
  onSaveError?: (ex: unknown, values: any) => void;
}

const leftIcon = {
  marginRight: '8px',
};

const RunEnvironmentEditor = ({
  runEnvironment,
  onSaveStarted,
  onSaveSuccess,
  onSaveError
}: Props) => {
  const runEnv = runEnvironment ?? makeNewRunEnvironment();

  const infraByName = runEnv.infrastructure_settings;

  const awsInfraByName = infraByName['AWS'];

  const defaultAws = awsInfraByName ? awsInfraByName['__default__'] : null;

  console.log(`defaultAws = ${JSON.stringify(defaultAws)}`);

  const ems = runEnv.execution_method_settings;
  const awsEcsEmsByName = ems['AWS ECS'];
  const defaultAwsEcsEms = awsEcsEmsByName ? awsEcsEmsByName['__default__'] : null;

  console.log(`defaultAwsEcsEms = ${JSON.stringify(defaultAwsEcsEms)}`);

  const [allowAwsControl, setAllowAwsControl] = useState(
    !!defaultAws || false
  );

  const context = useContext(GlobalContext);

  const {
    currentGroup
  } = context

  const accessLevel = accessLevelForCurrentGroup(context);
  const isSaveAllowed = accessLevel && (accessLevel >= ACCESS_LEVEL_DEVELOPER);

  if (!isSaveAllowed) {
    return (
      <p>
        You don&apos;t have permission to view this Run Environment&apos;s details.
        Contact the Group administrator to obtain permission.
      </p>
    );
  }

  const yupObjectShape = {
    name: Yup.string().max(1000).required(),
    description: Yup.string().max(5000)
  };

  if (allowAwsControl) {
    yupObjectShape['infrastructure_settings'] = Yup.object().shape({
      'AWS': Yup.object().shape({
        '__default__': Yup.object().shape({
          account_id: Yup.number().required().positive().integer(),
          region: Yup.string().max(20).required(),
          events_role_arn: Yup.string().max(1000).required(),
          assumed_role_external_id: Yup.string().max(1000).required(),
          workflow_starter_lambda_arn: Yup.string().max(1000),
          workflow_starter_access_key: Yup.string().max(1000),
        })
      })
    });

    Object.assign(yupObjectShape, {
      aws_account_id: Yup.number().required().positive().integer(),
      aws_default_region: Yup.string().max(20).required(),
      aws_events_role_arn: Yup.string().max(1000).required(),
      aws_assumed_role_external_id: Yup.string().max(1000).required(),
      aws_workflow_starter_lambda_arn: Yup.string().max(1000),
      aws_workflow_starter_access_key: Yup.string().max(1000),
      execution_method_capabilities: Yup.array().of(
        Yup.object().shape({
          type: Yup.string().max(100).required(),
          supported_launch_types: Yup.array()
            .of(Yup.string()).min(1).required()
        })
      )
    });
  }

  const validationSchema = Yup.object().shape(yupObjectShape);

  return (
    <Formik
      initialValues={runEnv}
      enableReinitialize={true}
      validationSchema={validationSchema}
      onSubmit={async (values, actions) => {
        try {
          if (!runEnvironment && currentGroup) {
            values.created_by_group = { id: currentGroup.id };
          }

          if (onSaveStarted) {
            onSaveStarted();
          }

          actions.setSubmitting(true);

          const uuid = runEnv.uuid || 'new';
          const saved = await saveRunEnvironment(uuid, values);

          actions.setSubmitting(false);

          if (onSaveSuccess) {
            onSaveSuccess(saved);
          }
        } catch (ex: unknown) {
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
        setFieldValue,
        errors,
        setErrors,
        isValid,
        touched,
        isSubmitting,
      }) => {
        const emc = values.execution_method_capabilities ?
          values.execution_method_capabilities[0] : null;
        const awsEcsEmc = (emc?.type === EXECUTION_METHOD_TYPE_AWS_ECS) ?
          (emc as any) : null;

        const handleAllowAwsControlChange = () => {
          const emcs = allowAwsControl ? [] : [{
            type: EXECUTION_METHOD_TYPE_AWS_ECS,
            supported_launch_types: ['FARGATE']
          }];
          setFieldValue('execution_method_capabilities', emcs);
          setErrors({});
          setAllowAwsControl(!allowAwsControl);
        };

        return (
          <Form noValidate onSubmit={handleSubmit}
            className="run_environment_settings_form">
            <fieldset disabled={!isSaveAllowed || isSubmitting}>
              <Row className="pb-3">
                <Col>
                  <FormikErrorsSummary errors={errors} touched={touched}
                    values={values}/>
                </Col>
              </Row>

              <SettingsForm items={commonItems} onChange={handleChange} />

              <div className={styles.formSection}>
                <h4 className={styles.sectionTitle}>Management</h4>
                <FormGroup controlId="awsEcsCheckbox">
                  <FormCheck label="Enable CloudReactor to manage Tasks in AWS"
                  checked={allowAwsControl}
                  onChange={handleAllowAwsControlChange} />
                </FormGroup>
              </div>

              {
                allowAwsControl && (
                  <Fragment>
                    <SettingsForm items={items1} onChange={handleChange} />

                    <div className={styles.formSection}>
                      <div className={styles.sectionTitle}>
                        AWS Networking
                      </div>
                      <FormGroup controlId="forDefaultSubnets">
                        <FormLabel>Default Subnets</FormLabel>
                        <div>
                          <FieldArray
                            name="execution_method_capabilities[0].default_subnets"
                            render={arrayHelpers => (
                              <Fragment>
                                {awsEcsEmc && awsEcsEmc.default_subnets && awsEcsEmc.default_subnets.length > 0 ? (
                                  awsEcsEmc.default_subnets.map((item: any, index: any) => (
                                    <InputGroup key={index} className="mb-3">
                                      <Field
                                        name={`execution_method_capabilities[0].default_subnets.${index}`}
                                        type="text"
                                        className="form-control"
                                      />
                                      <InputGroup.Append>
                                        <IconButton
                                          aria-label="delete"
                                          onClick={() => arrayHelpers.remove(index)} // remove an item from the list
                                        >
                                          <DeleteIcon />
                                        </IconButton>
                                      </InputGroup.Append>
                                    </InputGroup>
                                  ))
                                ) : null }
                                <Button
                                  variant="outlined"
                                  size="small"
                                  onClick={() => arrayHelpers.push('')}
                                  className={styles.button}
                                >
                                  <AddBoxIcon style={leftIcon} />
                                  Add subnet
                                </Button>
                              </Fragment>
                            )}
                          />
                        </div>
                      </FormGroup>
                    </div>
                    <div>
                      <FormGroup controlId="forDefaultSecurityGroups">
                        <FormLabel>Default Security Groups</FormLabel>
                        <div>
                          <FieldArray
                            name="execution_method_capabilities[0].default_security_groups"
                            render={arrayHelpers => (
                              <Fragment>
                                {awsEcsEmc?.default_security_groups ? (
                                  awsEcsEmc.default_security_groups.map((item: any, index: any) => (
                                    <InputGroup key={index} className="mb-3">
                                      <Field
                                        name={`execution_method_capabilities[0].default_security_groups.${index}`}
                                        type="text"
                                        className="form-control"
                                      />
                                      <InputGroup.Append>
                                        <IconButton
                                          aria-label="delete"
                                          onClick={() => arrayHelpers.remove(index)} // remove an item from the list
                                        >
                                          <DeleteIcon />
                                        </IconButton>
                                      </InputGroup.Append>
                                    </InputGroup>
                                  ))
                                ) : null }
                                <Button
                                  variant="outlined"
                                  size="small"
                                  onClick={() => arrayHelpers.push('')}
                                  className={styles.button}
                                >
                                  <AddBoxIcon style={leftIcon} />
                                  Add security group
                                </Button>
                              </Fragment>
                            )}
                          />
                        </div>
                      </FormGroup>
                    </div>

                    <SettingsForm items={items2} onChange={handleChange} />
                  </Fragment>
                )
              }

              {
                runEnvironment && (
                  <div className={styles.formSection}>
                    <div className={styles.sectionTitle}>
                      Notifications
                    </div>
                    <div>
                      <FormGroup controlId="forNotifications">
                        <FormLabel>Select default Alert Methods for Tasks & Workflows created in this Run Environment</FormLabel>
                        <FieldArray name="default_alert_methods" render={arrayHelpers => {
                          return (
                            <AlertMethodSelector
                              runEnvironmentUuid={runEnvironment?.uuid}
                              noAlertMethodsText="No Alert Methods scoped to this Run Environment are available."
                              selectedAlertMethodUuids={(values.default_alert_methods ?? []).map((am: any) => am.uuid)}
                              onSelectedAlertMethodsChanged={(alertMethods: AlertMethod[]) => {
                                let removed: (AlertMethod | undefined);
                                do {
                                  removed = arrayHelpers.remove(0);
                                } while (removed);
                                alertMethods.forEach(am => {
                                  arrayHelpers.push({ uuid: am.uuid });
                                });
                              }}
                            />
                          );
                        }}/>
                      </FormGroup>
                    </div>
                  </div>
                )
              }
              {
                isSaveAllowed && (
                  <Row className="pt-3 pb-3">
                    <Col>
                      <Button variant="outlined" color="primary" size="large" type="submit"
                        disabled={isSubmitting || (Object.keys(errors).length > 0)}>
                        Save
                      </Button>
                    </Col>
                  </Row>
                )
              }
            </fieldset>
          </Form>
        );
      }
      }
    </Formik>
  );
}

export default RunEnvironmentEditor;