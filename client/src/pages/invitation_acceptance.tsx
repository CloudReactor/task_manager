import { makeConfiguredClient, exceptionToErrorMessages } from '../axios_config';

import React, { Fragment, useState } from 'react';
import { useLocation } from 'react-router';
import { Link } from 'react-router-dom';

import {
  Alert,
  Button,
} from 'react-bootstrap';

import RegistrationLoginContainer from '../components/RegistrationLogin/RegistrationLoginContainer';

import * as path from '../constants/routes';

interface Props {
}

const InvitationAcceptance = (props: Props) => {
  const [activated, setActivated] = useState(false);
  const [header, setHeader] = useState('Email verified!');
  const [errorMessages, setErrorMessages] = useState<string[]>([]);

  const location = useLocation();

  const handleSubmit = async (): Promise<void> => {
    const urlParams = new URLSearchParams(location.search);
    const code = urlParams.get('code');

    console.log('submitting invitation acceptance');

    try {
      await makeConfiguredClient().post(
        'api/v1/invitations/accept', {
          confirmation_code: code
        });

      setActivated(true);
      setHeader('Account activated!');
    } catch (ex) {
      setErrorMessages(exceptionToErrorMessages(ex));
    }
  }

  return (

    <RegistrationLoginContainer heading={header}>
      <Fragment>
        {
          activated ? (
            <div style={{textAlign: 'center'}}>
              <p>
                Thanks for activating your CloudReactor account. You may now <Link to={path.LOGIN}>sign in</Link>.
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

              <div style={{textAlign: 'center'}}>
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
      </Fragment>
    </RegistrationLoginContainer>
  );
}

export default InvitationAcceptance;
