import React, { Component } from "react";
import Alert from 'react-bootstrap/Alert';
import CustomInput from '../../../components/forms/CustomInput'
import { makeAuthenticatedClient, exceptionToErrorMessages } from '../../../axios_config'
import { withRouter, RouteComponentProps } from "react-router";
import { Formik, Field, Form } from 'formik';
import * as yup from 'yup';
import items from './passwordInputs';
import CustomButton from '../../../components/common/Button/CustomButton';
import styles from './ProfileEditor.module.scss';


type PathParamsType = {
  uuid: string;
};

type Props = RouteComponentProps<PathParamsType> & {
}

interface State {
  errorMessages: string[];
  success: boolean;
}

interface Values {
  current_password: string;
  new_password: string;
  re_new_password: string;
}

const initialValues: Values = {
  current_password: '',
  new_password: '',
  re_new_password: '',
};

const setPasswordSchema = yup.object().shape({
  current_password: yup.string().trim()
    .required('Current password is required'),

  new_password: yup.string().trim()
    .min(8, 'Password has to be at least 8 characters.')
    .max(32, 'Password can be a maximum of 32 characters.')
    .required('New password is required'),

  re_new_password: yup.string().trim()
    .oneOf([yup.ref('new_password')], 'Passwords must match.')
    .required('Please confirm new password'),
});

class ProfileEditor extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    this.state = {
      errorMessages: [],
      success: false,
    };
  }

  public render() {

    return (
      <div className={styles.container}>
        { this.state.errorMessages.length > 0 &&
          <Alert variant="danger">
            {this.state.errorMessages}
          </Alert>
        }
        { this.state.success &&
          <Alert variant="success">
            Password changed!
          </Alert>
        }
        <h1>Change password</h1>
        
        <Formik
          validateOnBlur
          validateonChange
          initialValues={initialValues}
          validationSchema={setPasswordSchema}
          onSubmit={async (values: Values, actions: any) => {
            this.setState({
              errorMessages: [],
              success: false,
            })

            try {
              const response = await makeAuthenticatedClient().post('auth/users/set_password/', values);
              
              if (response.status === 204) {
                this.setState({
                  success: true,
                });
              }
              actions.setSubmitting(false);
              
            } catch (ex) {
              this.setState({                
                errorMessages: exceptionToErrorMessages(ex)
              });
            }         
          }}
        >
          {({ isSubmitting, handleChange, handleBlur }) => (
            <Form>
              {items.map((item) => {
                const {label, name, placeholder} = item || {};
                return (
                  <div className={styles.fieldGroup} key={name}>
                    <label htmlFor={name}>{label}</label>
                    <Field
                      id={name}
                      name={name}
                      type="password"
                      component={CustomInput}
                      onBlur={handleBlur}
                      placeholder={placeholder}
                      onChange={handleChange}
                    />
                  </div>
                );
              })}
              <CustomButton
                color="primary"
                type="submit"
                disabled={isSubmitting}
                label="Change password"
              />
            </Form>
          )}
        </Formik>
      </div>
    );
  }
}

export default withRouter(ProfileEditor);