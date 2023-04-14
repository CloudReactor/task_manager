import { makeConfiguredClient, exceptionToErrorMessages } from '../axios_config';

import React, { Fragment, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import {
  Alert,
  Button,
} from 'react-bootstrap';

import RegistrationLoginContainer from '../components/RegistrationLogin/RegistrationLoginContainer';

import * as path from '../constants/routes';
import styles from './registration_activation.module.scss';
import abortableHoc, { AbortSignalProps } from '../hocs/abortableHoc';

const RegistrationActivation = (props: AbortSignalProps) => {
  const {
    abortSignal
  } = props;

  const [activated, setActivated] = useState(false);
  const [header, setHeader] = useState('Email verified!');
  const [errorMessages, setErrorMessages] = useState<string[]>([]);

  const location = useLocation();
  const urlParams = new URLSearchParams(location.search);
  const uid = urlParams.get('uid');
  const token = urlParams.get('token');

  console.log(`uid = ${uid}, token = ${token}`);

  const handleSubmit = async () => {
    console.log(`submitted activation for user ${uid}`);

    try {
      await makeConfiguredClient().post('auth/users/activation/', {
        uid,
        token
      }, {
        signal: abortSignal
      });

      setActivated(true);
      setHeader('Account activated!');
    } catch (ex) {
      setErrorMessages(exceptionToErrorMessages(ex));
    }
  }

  return (
    <RegistrationLoginContainer heading={header}>
      <div className={styles.activation}>
        {
          activated ? (
            <div>
              <p>
                Thanks for activating your CloudReactor account. You may
                now <Link to={path.LOGIN + '?status=activated'}>sign in</Link>.
              </p>
            </div>
          ) : (
            <Fragment>
              {
                (errorMessages.length > 0) &&
                <Alert variant="danger">
                  <ul>
                    {
                      errorMessages.map(err => {
                        const s = (err || '').toString();
                        return <li key={s}>{s}</li>;
                      })
                    }
                  </ul>
                </Alert>
              }

              <div>
                <p>
                  Click the button below to finish creating your CloudReactor account.
                </p>
              </div>
              <div style={{display: 'flex', justifyContent: 'center', marginTop: '40px'}}>
                <Button size="lg" onClick={handleSubmit}>Activate</Button>
              </div>
            </Fragment>
          )
        }
      </div>
    </RegistrationLoginContainer>
  );
}

export default abortableHoc(RegistrationActivation);
