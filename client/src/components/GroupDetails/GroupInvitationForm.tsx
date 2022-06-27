import { ACCESS_LEVEL_OBSERVER, ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';
import { Group } from '../../types/website_types';

import React from 'react';

import {
  Form,
  Col
} from 'react-bootstrap';

import * as Yup from 'yup';

import { Formik, Field, ErrorMessage } from 'formik';

import ActionButton from '../common/ActionButton';
import AccessLevelSelector from '../common/AccessLevelSelector';

interface Props {
  group: Group;
  onSubmit: (values: any) => Promise<void>;
}

const invitationSchema = Yup.object().shape({
  to_email: Yup.string().email().required('Email is required.').max(150),
  access_level: Yup.number().integer().min(0)
});

export default function GroupInvitationForm({ group, onSubmit }: Props) {
  return (
    <Formik initialValues={{
        to_email: '',
        group_access_level: '' + ACCESS_LEVEL_DEVELOPER
      }}
      validationSchema={invitationSchema}
      onSubmit={async (values, actions) => {
        const invitation: any = {
          to_email: values.to_email,
          group: {
            id: group.id
          }
        };

        if (values.group_access_level) {
          const groupAccessLevel = parseInt(values.group_access_level);

          if (groupAccessLevel > ACCESS_LEVEL_OBSERVER) {
            invitation.group_access_level = groupAccessLevel;
          }
        }

        await onSubmit(invitation);
        actions.resetForm();
        actions.setFieldTouched('to_email', false, false);
      }}
    >
      {({ errors, isSubmitting, handleReset, handleSubmit }) => (
        <Form onReset={handleReset} onSubmit={(e) => { if (e) { handleSubmit(e as any); } }}>
          <Form.Row>
            <Form.Group as={Col} controlId="formGridEmail">
              <Form.Label className="mb-2 mr-sm-2" >Email address</Form.Label>
              <Field name="to_email" type="email"
               placeholder="Enter email" className="mb-2 mr-sm-2" as={Form.Control} />
            </Form.Group>
            <Form.Group as={Col} controlId="formGridAccessLevel">
              <Form.Label className="mb-2 mr-sm-2">Access level</Form.Label>
              <Field name="group_access_level">
                {
                  ({ field }) => (
                    <AccessLevelSelector {...field} />
                  )
                }
              </Field>
            </Form.Group>
            <Form.Group as={Col}>
              <ActionButton label="Invite" style={{ marginTop: 30 }} inProgress={isSubmitting}
               size="large" onActionRequested={(action, cbData) => handleSubmit()} />
            </Form.Group>
          </Form.Row>
          <Form.Row>
            {
              Object.keys(errors).map(fieldName => (
                <ErrorMessage key={fieldName} name={fieldName} />
              ))
            }
          </Form.Row>
        </Form>
      )}
    </Formik>
  );
}