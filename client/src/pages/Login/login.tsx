import React, { useContext, useState } from "react";
import { useNavigate, useLocation } from 'react-router-dom';

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

type Props = Record<string, never>;

export default function Login(props: Props) {
  const context = useContext(GlobalContext);
  const { setCurrentUser, setCurrentGroup } = context;

  const history = useNavigate();

  const [
    errorMessage,
    setErrorMessage
  ] = useState('');

  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const nextPath = params.get('next') || '/';

  const handleSubmit = async (values: { email: string; password: string; }): Promise<void> => {
    setErrorMessage('');
    const userLogin = { username: values.email, password: values.password }

    try {
      const tokenResponse = await makeConfiguredClient().post('auth/jwt/create/', userLogin);
      JwtUtils.saveToken(tokenResponse.data);
      const user = await fetchCurrentUser();
      setCurrentUser(user);
      setCurrentGroup(user.groups[0]);
      history(nextPath, { state: { user } });
    } catch (error) {
      console.log(error);
      setErrorMessage('Incorrect username or password');
    }
  }

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
        handleSubmit={handleSubmit}
        errorMessage={errorMessage}
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
