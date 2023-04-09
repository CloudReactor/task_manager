import React, { Component } from "react";
import { withRouter } from 'react-router-dom';
import { RouteComponentProps } from 'react-router';

import {
  Alert
} from 'react-bootstrap';

import { makeConfiguredClient } from '../../axios_config';
import { fetchCurrentUser } from '../../utils/api';

import { GlobalContext } from '../../context/GlobalContext';
import RegistrationLoginContainer from '../../components/RegistrationLogin/RegistrationLoginContainer';
import LoginForm from '../../components/RegistrationLogin/LoginForm';
import formItems from './loginFormItems';

import * as JwtUtils from '../../utils/jwt_utils';

const DEPLOYMENT = import.meta.env.VITE_DEPLOYMENT ?? 'N/A';
const VERSION_SIGNATURE = import.meta.env.VITE_VERSION_SIGNATURE ?? 'N/A';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/';

interface Props extends RouteComponentProps {
}

interface State {
  errorMessage?: string;
}

 class Login extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    this.state = {};
  }

  private handleSubmit = async (values: { email: string; password: string; }): Promise<void> => {
    this.setState({errorMessage: undefined});
    const userLogin = { username: values.email, password: values.password }

    try {
      const tokenResponse = await makeConfiguredClient().post('auth/jwt/create/', userLogin);
      JwtUtils.saveToken(tokenResponse.data);

      const user = await fetchCurrentUser();

      const { setCurrentUser, setCurrentGroup } = this.context;
      setCurrentUser(user);
      setCurrentGroup(user.groups[0]);

      const nextPath = new URL(window.location.href).searchParams.get('next') || '/';
      this.setState({ errorMessage: undefined }, () => {
        this.props.history.push(nextPath, user);
      });
    } catch (error) {
      console.log(error);
      this.setState({errorMessage: 'Incorrect username or password'});
    }
  }

  public render() {
    const {
      location
    } = this.props;

    const params = new URLSearchParams(location.search);
    const status = params.get('status');

    return (
      <RegistrationLoginContainer heading="Sign in to your account">
        {
          (status === 'activated') &&
          <Alert variant='info'>
            <Alert.Heading>Account activated</Alert.Heading>
            <p>
              Your account has been activated. Please sign in with the credentials
              you just entered.
            </p>
          </Alert>
        }

        <LoginForm
          handleSubmit={this.handleSubmit}
          errorMessage={this.state.errorMessage}
          formItems={formItems}
        />
        {
          (DEPLOYMENT !== 'production') &&
          <div>
            <p>Version: {VERSION_SIGNATURE}</p>
            <p>API Base URL: {API_BASE_URL ?? 'Undefined'}</p>
          </div>
        }
      </RegistrationLoginContainer>
    );
  }
}

export default withRouter(Login);
