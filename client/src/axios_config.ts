import axios from 'axios';

import createAuthRefreshInterceptor from 'axios-auth-refresh';

import * as JwtUtils from './utils/jwt_utils';

axios.defaults.withCredentials = true;

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/';

const defaultOptions = {
  baseURL,
  'Access-Control-Allow-Origin': '*',
  'Content-Type': 'application/json',
  'X-Requested-With': 'XMLHttpRequest'
};


export const makeConfiguredClient = () => {
  return axios.create(defaultOptions);
};

// Function that will be called to refresh authorization
const refreshAuthLogic = (failedRequest: any): Promise<any> => {
  const refresh = JwtUtils.readTokenContainer().refresh;
  return axios.post(baseURL + 'auth/jwt/refresh', {
    refresh
  }).then(tokenRefreshResponse => {
    JwtUtils.saveToken(tokenRefreshResponse.data);
    failedRequest.response.config.headers['Authorization'] = 'JWT ' + tokenRefreshResponse.data.access;
    return Promise.resolve();
  }).catch(e => {
    console.log('Failed to refresh authorization, redirecting to login page ...');
    window.location.href = '/login?next=' + encodeURIComponent(
      window.location.pathname + window.location.search + window.location.hash);
  });
}

export const makeAuthenticatedClient = () => {
  const token = JwtUtils.readTokenContainer().access;

  const ax = axios.create(Object.assign({
    headers: {
      'Authorization': `JWT ${token}`
    }
  }, defaultOptions));

  createAuthRefreshInterceptor(ax, refreshAuthLogic);

  return ax;
};

export function exceptionToErrorMessages(ex: any): string[] {
  if (ex.response && ex.response.data) {
    const data = ex.response.data;

    // Don't try to read string bodies which are likely HTML.
    if (data && (typeof data !== 'string')) {
      const errorMessages = Object.keys(data).filter(key => !key.startsWith('error'))
        .flatMap(key => data[key]);

      if (errorMessages.length > 0) {
        return errorMessages;
      }

      if (data.error_message) {
        return [data.error_message];
      }
    }
  }

  if (ex.message) {
    return [ex.message];
  }

  return ['An unknown error occurred. Please contact support@cloudreactor.io for help.']
}