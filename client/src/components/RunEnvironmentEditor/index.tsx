import {
  ACCESS_LEVEL_DEVELOPER,
  INFRASTRUCTURE_TYPE_AWS,
  AWS_ACCOUNT_ID_REGEXP,
  AWS_REGIONS,
  AWS_ROLE_ARN_REGEXP,
  AWS_SECURITY_GROUP_REGEXP,
  AWS_SUBNET_REGEXP,
  AWS_ECS_CLUSTER_ARN_REGEXP,
  AWS_LAMBDA_ARN_REGEXP,
  EXECUTION_METHOD_TYPE_AWS_ECS,
  AWS_ECS_LAUNCH_TYPE_FARGATE,
  AWS_ECS_ALL_SUPPORTED_LAUNCH_TYPES,
  AWS_ECS_PLATFORM_VERSIONS
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

import React, { useContext, Fragment } from 'react';

import {
  Col,
  Row,
  FormGroup,
  FormLabel,
  InputGroup,
} from 'react-bootstrap';

import { ErrorMessage, Field, FieldArray, Form, Formik  } from 'formik';

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

import SettingsForm from '../../components/forms/SettingsForm';
import styles from './index.module.scss';

const BASE_ITEMS = [{
  title: 'General',
  controls: [{
    name: 'name',
    label: 'Name',
    type: 'text',
    controlId: 'forName',
    placeholder: 'e.g. Production, Staging',
  }, {
    name: 'description',
    label: 'Description',
    type: 'text',
    controlId: 'forDescription',
    placeholder: 'Description of this environment',
  }],
}];

const AWS_INFRASTRUCTURE_ITEMS = [{
  title: 'AWS General Settings',
  controls: [{
    name: `infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.account_id`,
    label: 'Account ID',
    type: 'text',
    controlId: 'forAwsAccountId',
    placeholder: '123456789012',
  }, {
    name: `infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.region`,
    label: 'Default Region',
    type: 'select',
    controlId: 'forAwsRegion',
    placeholder: '',
    options: AWS_REGIONS
  }],
},{
  title: 'CloudReactor Access',
  controls: [{
    name: `infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.events_role_arn`,
    label: 'Role for CloudReactor to Assume',
    type: 'text',
    controlId: 'forAwsEventsRoleArn',
    placeholder: 'arn:aws:iam::123456789012:role/CloudReactor-staging-executionSchedulingRole-XXX',
    subText: 'The name or ARN of a role that is assumable by CloudReactor, giving it permission to manage your Tasks'
  }, {
    name: `infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.assumed_role_external_id`,
    label: 'External ID',
    type: 'text',
    controlId: 'forAwsAssumedRoleExternalId',
    placeholder: 'SomeKey',
    subText: 'A secret value that is used to authenticate management requests are from CloudReactor.'
  }, {
    name: `infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.workflow_starter_lambda_arn`,
    label: 'Workflow Starter Lambda',
    type: 'text',
    controlId: 'forAwsWorkflowStarterLambdaArn',
    placeholder: 'arn:aws:lambda:us-west-2:123456789012:function:CloudReactor-staging-workflowStarterLambda-XXX',
    subText: 'The name or ARN of the Lambda function, installed by the CloudReactor role CloudFormation template, that starts Workflows'
  }, {
    name: `infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.workflow_starter_access_key`,
    label: 'Workflow Starter Access Key',
    type: 'text',
    controlId: 'forAwsWorkflowStarterAccessKey',
    placeholder: 'SomeKey',
    subText: 'A secret value that is used to authenticate requests to start Workflows are from CloudReactor'
  }
  ],
}];

const AWS_EXTRA_ITEMS = [{
  controls: [
    {
      name: `infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.assign_public_ip`,
      label: 'Assign Public IP by Default',
      type: 'checkbox',
      controlId: 'forExecutionMethodCapabilitiesDefaultAssignPublicIp',
      subText: 'Check if your Tasks should be given a public IP when executed. This should be checked if you run your Tasks in a public subnet.',
    }
  ]
}];

const AWS_ECS_EXECUTION_METHOD_ITEMS = [{
  title: 'AWS ECS Settings',
  controls: [{
    name: `execution_method_settings.${EXECUTION_METHOD_TYPE_AWS_ECS}.__default__.settings.cluster_arn`,
    label: 'ECS Cluster',
    type: 'text',
    controlId: 'forExecutionMethodCapabilitiesDefaultClusterArn',
    placeholder: 'staging',
    subText: 'The name or ARN of the default ECS cluster used to run Tasks',
  }, {
    name: `execution_method_settings.${EXECUTION_METHOD_TYPE_AWS_ECS}.__default__.settings.execution_role_arn`,
    label: 'Task Execution Role',
    type: 'text',
    controlId: 'forExecutionMethodCapabilitiesDefaultExecutionRole',
    placeholder: 'arn:aws:iam::123456789012:role/staging-taskExecutionRole-XXX',
    subText: 'The name or ARN of a role that is used to start ECS tasks, which should be assumable by the CloudReactor Role'
  }, {
    name: `execution_method_settings.${EXECUTION_METHOD_TYPE_AWS_ECS}.__default__.settings.task_role_arn`,
    label: 'Default Task Role',
    type: 'text',
    controlId: 'forExecutionMethodCapabilitiesDefaultTaskRole',
    placeholder: 'arn:aws:iam::123456789012:role/staging-taskRole-XXX',
    subText: 'Optional. The name or ARN of a role that gives Tasks running in this Run Environment access to other AWS resources.',
  }, {
    name: `execution_method_settings.${EXECUTION_METHOD_TYPE_AWS_ECS}.__default__.settings.supported_launch_types`,
    label: 'Supported Launch Types',
    type: 'select',
    controlId: 'forExecutionMethodCapabilitiesSupportedLaunchTypes',
    options: AWS_ECS_ALL_SUPPORTED_LAUNCH_TYPES,
    multiple: true
  }, {
    name: `execution_method_settings.${EXECUTION_METHOD_TYPE_AWS_ECS}.__default__.settings.platform_version`,
    label: 'Default Platform Version',
    type: 'select',
    controlId: 'forExecutionMethodCapabilitiesDefaultPlatformVersion',
    placeholder: '1.4.0',
    options: AWS_ECS_PLATFORM_VERSIONS,
    subText: 'Optional. Specifies the ECS platform version. Defaults to 1.4.0.',
  }],
}];

type Props = {
  runEnvironment?: RunEnvironment;
  onSaveStarted?: (runEnvironment: RunEnvironment) => void;
  onSaveSuccess?: (runEnvironment: RunEnvironment) => void;
  onSaveError?: (ex: unknown, values: any) => void;
  debugMode?: boolean;
}

const leftIcon = {
  marginRight: '8px',
};

const RunEnvironmentEditor = ({
  runEnvironment,
  onSaveStarted,
  onSaveSuccess,
  onSaveError,
  debugMode
}: Props) => {
  const runEnv = runEnvironment ?? makeNewRunEnvironment();

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
    description: Yup.string().max(5000),
    infrastructure_settings: Yup.object().shape({
      'AWS': Yup.object().shape({
        '__default__': Yup.object().shape({
          settings: Yup.object().shape({
            account_id: Yup.string().matches(AWS_ACCOUNT_ID_REGEXP,
              'AWS Account ID must be 12 digits').nullable(),
            region: Yup.string().oneOf(AWS_REGIONS),
            events_role_arn: Yup.string().max(1000).matches(AWS_ROLE_ARN_REGEXP,
              'CloudReactor Role ARN is invalid'),
            assumed_role_external_id: Yup.string().max(1000).nullable(),
            workflow_starter_lambda_arn: Yup.string().max(1000).matches(AWS_LAMBDA_ARN_REGEXP,
              'Workflow Starter Lambda ARN is invalid'),
            workflow_starter_access_key: Yup.string().max(1000).nullable(),
            network: Yup.object().shape({
              subnets: Yup.array().of(Yup.string().required(
                'Subnet must not be blank').matches(
                AWS_SUBNET_REGEXP,
                'Subnet is invalid, must start with "subnet-", followed by 8 or 17 lower-case hexadecimal digits')),
              security_groups: Yup.array().of(Yup.string().required(
                'Security Group must not be blank').matches(
                AWS_SECURITY_GROUP_REGEXP,
                'Security Group is invalid, must start with "sg-", followed by 8 or 17 lower-case hexadecimal digits')),
              assign_public_ip: Yup.boolean().default(false)
            }).nullable(),
            logging: Yup.object().shape({
              driver: Yup.string().nullable(),
              options: Yup.object().shape({
                create_group: Yup.string().nullable(),
                datetime_format: Yup.string().nullable(),
                multiline_pattern: Yup.string().nullable(),
                // mode: Yup.string(),
                // max_buffer_size: Yup.string(),
              }).nullable()
            }).nullable(),
            tags: Yup.object().nullable()
          })
        }).nullable()
      }).nullable()
    }),
    execution_method_settings: Yup.object().shape({
      'AWS ECS': Yup.object().shape({
        '__default__': Yup.object().shape({
          settings: Yup.object().shape({
            'launch_type': Yup.string().oneOf(AWS_ECS_ALL_SUPPORTED_LAUNCH_TYPES)
              .default(AWS_ECS_LAUNCH_TYPE_FARGATE),
            'supported_launch_types': Yup.array(Yup.string().oneOf(AWS_ECS_ALL_SUPPORTED_LAUNCH_TYPES)),
            'cluster_arn': Yup.string().matches(AWS_ECS_CLUSTER_ARN_REGEXP,
              'AWS ECS Cluster ARN is invalid, must be in the format "arn:aws:ecs:us-east-1:012345678901:cluster/example"').nullable(),
            'execution_role_arn': Yup.string().matches(AWS_ROLE_ARN_REGEXP,
              'Task Execution Role ARN is invalid, must start with "arn:"').nullable(),
            'task_role_arn': Yup.string().matches(AWS_ROLE_ARN_REGEXP,
              'Default Task Role ARN is invalid, must start with "arn:"').nullable(),
            'platform_version': Yup.string()
          }).nullable()
        }).nullable()
      }).nullable()
    })
  };

  const validationSchema = Yup.object().shape(yupObjectShape);

  return (
    <Formik
      initialValues={runEnv}
      enableReinitialize={true}
      validationSchema={validationSchema}
      validateOnChange={true}
      validateOnMount={true}
      onSubmit={async (values, actions) => {
        try {
          if (!runEnvironment && currentGroup) {
            values.created_by_group = { id: currentGroup.id };
          }

          if (onSaveStarted) {
            onSaveStarted(values);
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
        handleBlur,
        values,
        errors,
        isValid,
        touched,
        isSubmitting,
      }) => {
        const infraByName = values.infrastructure_settings;

        const awsInfraByName = infraByName['AWS'];

        const defaultAws = awsInfraByName ? awsInfraByName['__default__'] : null;
        const defaultAwsSettings = defaultAws ? defaultAws['settings'] : null;

        if (debugMode) {
          console.log(`isValid = ${isValid}, errors = `);
          console.dir(errors);
        }

        return (
          <Form className="run_environment_settings_form">
            <fieldset disabled={isSubmitting}>
              {
                debugMode && (
                  <Row className="pb-3">
                    <Col>
                      <FormikErrorsSummary errors={errors} touched={touched}
                        values={values}/>
                    </Col>
                  </Row>
                )
              }

              <SettingsForm items={BASE_ITEMS}
               onChange={handleChange} onBlur={handleBlur} />

              <Fragment>
                <SettingsForm items={AWS_INFRASTRUCTURE_ITEMS}
                 onChange={handleChange} onBlur={handleBlur} />

                <div className={styles.formSection}>
                  <div className={styles.sectionTitle}>
                    AWS Networking
                  </div>
                  <FormGroup controlId="forDefaultSubnets">
                    <FormLabel>Default Subnets</FormLabel>
                    <div>
                      <FieldArray
                        name={`infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.network.subnets`}
                        render={arrayHelpers => (
                          <Fragment>
                            {
                              (defaultAwsSettings?.network?.subnets || []).map((item: any, index: any) => (
                                <Fragment key={index}>
                                  <InputGroup className="mb-1">
                                    <Field
                                      name={`infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.network.subnets.${index}`}
                                      type="text"
                                      className="form-control"
                                    />
                                    <InputGroup.Append className={styles.deleteButtonInputGroupAppend}>
                                      <IconButton
                                        aria-label="delete"
                                        onClick={() => { arrayHelpers.remove(index); }}>
                                        <DeleteIcon/>
                                      </IconButton>
                                    </InputGroup.Append>
                                  </InputGroup>
                                  <ErrorMessage name={`infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.network.subnets[${index}]`}
                                   render={msg => <div className="error text-danger mb-2">{msg}</div>} />
                                </Fragment>
                              ))
                            }
                            <Button
                              variant="outlined"
                              size="small"
                              onClick={() => arrayHelpers.push('')}
                              className={styles.button}>
                              <AddBoxIcon style={leftIcon} />
                              Add Subnet
                            </Button>
                          </Fragment>
                        )}
                      />
                    </div>
                  </FormGroup>
                  <FormGroup controlId="forDefaultSecurityGroups">
                    <FormLabel>Default Security Groups</FormLabel>
                    <div>
                      <FieldArray
                        name={`infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.network.security_groups`}
                        render={arrayHelpers => (
                          <Fragment>
                            {
                              (defaultAwsSettings?.network?.security_groups || []).map((item: any, index: any) => (
                                <Fragment key={index}>
                                  <InputGroup className="mb-1">
                                    <Field
                                      name={`infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.network.security_groups.${index}`}
                                      type="text"
                                      className="form-control"
                                    />
                                    <InputGroup.Append className={styles.deleteButtonInputGroupAppend}>
                                      <IconButton
                                        aria-label="delete"
                                        onClick={() => {
                                          arrayHelpers.remove(index);
                                        }}>
                                        <DeleteIcon />
                                      </IconButton>
                                    </InputGroup.Append>
                                  </InputGroup>
                                  <ErrorMessage name={`infrastructure_settings.${INFRASTRUCTURE_TYPE_AWS}.__default__.settings.network.security_groups[${index}]`}
                                   render={msg => <div className="error text-danger mb-2">{msg}</div>} />
                                </Fragment>
                              ))
                            }
                            <Button
                              variant="outlined"
                              size="small"
                              onClick={() => arrayHelpers.push('')}
                              className={styles.button}
                            >
                              <AddBoxIcon style={leftIcon} />
                              Add Security Group
                            </Button>
                          </Fragment>
                        )}
                      />
                    </div>
                  </FormGroup>
                  <SettingsForm items={AWS_EXTRA_ITEMS}
                   onChange={handleChange} onBlur={handleBlur} />
                  <SettingsForm items={AWS_ECS_EXECUTION_METHOD_ITEMS}
                   onChange={handleChange} onBlur={handleBlur} />
                </div>
              </Fragment>

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
                              entityTypeLabel="Run Environment"
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

              <Row className="pt-3 pb-3">
                <Col>
                  <Button variant="outlined" size="large" type="submit"
                    disabled={!isValid || isSubmitting || (Object.keys(errors).length > 0)}>
                    Save
                  </Button>
                </Col>
              </Row>
            </fieldset>
          </Form>
        );
      }
      }
    </Formik>
  );
}

export default RunEnvironmentEditor;
