import React from 'react';
import { Link } from 'react-router-dom';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import styles from './forms.module.scss';
import { Button } from 'react-bootstrap';

import * as path from '../../constants/routes';

import CustomInput from '../forms/CustomInput';

export interface Props {
  handleSubmit: (values: any) => Promise<void>;
  errorMessage: any;
  formItems: any[];
}

const loginSchema = Yup.object().shape({
  email: Yup.string().trim().required('Email is required.'),
  password: Yup.string()
    .required('Password is required.').min(8)
});

export default function LoginForm({ handleSubmit, errorMessage, formItems }: Props) {
  return (
    <Formik
      initialValues={{
        email: '',
        password: ''
      }}
      validationSchema={loginSchema}
      onSubmit={async (values, actions) => {
        handleSubmit(values);
      }}
    >
      {({ isSubmitting, handleChange }) => (
        <div className={styles.formContainer}>
          <Form>
            {formItems.map((item, i) => {
              const {
                name,
                label,
                type,
                controlId,
                placeholder,
              } = item || {};

              return (
                <Field
                  key={`login-input-${i}`}
                  name={name}
                  type={type}
                  label={label}
                  controlId={controlId}
                  placeholder={placeholder}
                  component={CustomInput}
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
                Sign In
              </Button>
            </div>
            <div className={styles.loginError}>
                { errorMessage }
            </div>
          </Form>
          <div className={styles.signUpOrLogin}>Need a CloudReactor account? <Link to={path.REGISTER}>Sign up</Link></div>
        </div>
      )}
    </Formik>

  );
}
