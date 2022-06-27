import React from 'react';
import { Link } from 'react-router-dom';
import { Formik, Form, Field } from 'formik';
import CustomInput from '../forms/CustomInput';
import styles from './forms.module.scss';

import {
  Alert,
  Button,
} from 'react-bootstrap';

import * as yup from 'yup';

import * as path from '../../constants/routes';

import { Invitation } from '../../types/website_types';

export interface Props {
  handleSubmit: (values: any) => Promise<void>;
  errorMessages: string[];
  items: any[];
  invitation?: Invitation | null;
}

interface Values {
  password: string;
  password_verification: string;
  email: string;
}

const registrationSchema = yup.object().shape({
  password: yup.string().trim()
    .min(8, 'Password has to be at least 8 characters.')
    .max(32, 'Password can be a maximum of 32 characters.')
    .required('Password is required.'),

  password_verification: yup.string().trim()
    .required('Password verification is required.')
    .oneOf([yup.ref('password')], 'Passwords must match.'),

  email: yup.string().trim().email('Email address is not valid.')
    .required('Email is required.').max(150)
});

export default function RegistrationForm({ handleSubmit, errorMessages, items, invitation }: Props) {
  const initialValues: Values = {
    password: '',
    password_verification: '',
    email: '',
  };

  if (invitation) {
    initialValues.email = invitation.to_email;
  }

  return (
    <div>
      <Formik
        initialValues={initialValues}
        enableReinitialize={true}
        validationSchema={registrationSchema}
        onSubmit={async (values: any, actions: any) => {
          handleSubmit(values);
        }}
      >
        {
          ({
            values, errors, touched, isSubmitting, submitCount, handleChange
          }) => {
            const allErrorMessages = (submitCount === 0) ? errorMessages :
              errorMessages.concat(
                Object.values(errors) as string[]);

            return (
            <div className={styles.formContainer}>
              <Form>
                {
                  (allErrorMessages.length > 0) &&
                <Alert variant="danger">
                  <ul style={{ marginBottom: '0'}}>
                      {
                        allErrorMessages.map(err => {
                          const s = (err || '').toString();
                          return <li key={s}>{s}</li>;
                        })
                      }
                    </ul>
                  </Alert>
                }

                {items.map((item, i) => {
                  const {
                    name,
                    label,
                    type,
                    controlId,
                    placeholder,
                    subText,
                  } = item || {};

                  const readOnly = invitation && (name === 'email');

                  return (
                    <Field
                      key={`registration-input-${i}`}
                      name={name}
                      type={type}
                      readOnly={readOnly}
                      label={label}
                      controlId={controlId}
                      placeholder={placeholder}
                      component={CustomInput}
                      subText={subText}
                      onChange={handleChange}
                    />
                  );
                })}

                <div className={styles.buttonContainer}>
                  <Button
                    className={styles.button}
                    type="submit"
                  >
                    {
                      isSubmitting &&
                      <i className="fas fa-circle-notch fa-spin fa-lg" />
                    }
                    Create account
                  </Button>
                </div>
              </Form>
              <div className={styles.signUpOrLogin}>Have an account already? <Link to={path.LOGIN}>Sign in</Link></div>
            </div>
            );
          }
        }
      </Formik>
    </div>
  );
}
