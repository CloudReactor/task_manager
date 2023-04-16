import { UserRegistration, Invitation } from '../../types/website_types';
import { makeConfiguredClient, exceptionToErrorMessages } from '../../axios_config';
import { fetchInvitation } from '../../utils/api';

import React, { Fragment, useEffect, useState } from 'react';

import { useHistory, useLocation } from 'react-router-dom';

import { Row, Col, Alert } from 'react-bootstrap'

import items from './registrationFormItems';
import RegistrationLoginContainer from '../../components/RegistrationLogin/RegistrationLoginContainer';
import RegistrationForm from '../../components/RegistrationLogin/RegistrationForm';

import * as path from '../../constants/routes';

import styles from './register.module.scss';

interface Props {
}

const Register = (props: Props) => {
  const location = useLocation();

  const params = new URLSearchParams(location.search);
  const invitationCode = params.get('invitation_code');
  const [isLoadingInvitation, setIsLoadingInvitation] = useState(false);
  const [errorMessages, setErrorMessages] = useState<string[]>([]);
  const [invitation, setInvitation] = useState<Invitation | null>(null);
  const history = useHistory();

  useEffect(() => {
    if (invitationCode && !isLoadingInvitation) {

      fetchInvitation(invitationCode).then(i => {
        setInvitation(i);
        setIsLoadingInvitation(false);
      });
    }
  }, [invitationCode, isLoadingInvitation]);

  const handleSubmit = async (values: UserRegistration) => {
    setErrorMessages([]);

    try {
      if (invitation) {
        Object.assign(values, { confirmation_code: invitationCode });
        await makeConfiguredClient().post('api/v1/invitations/accept/', values);
        history.replace(path.LOGIN + '?status=activated');
      } else {
        // Use email as username so we don&apos;t have to ask user to come up with a username
        const bodyObj = Object.assign(values, { username: values.email });
        await makeConfiguredClient().post('auth/users/', bodyObj);

        history.replace(path.REGISTRATION_PENDING +
          '?email=' + encodeURIComponent(values.email));
      }
    } catch (ex) {
      setErrorMessages(exceptionToErrorMessages(ex));
    }
  }

  return (
    <RegistrationLoginContainer heading="Create your account">
      <div>
      {

        isLoadingInvitation ? (
          <Row>
            <Col className={styles.loading}>
              <i className="fas fa-spin fa-circle-notch" />
              Loading your CloudReactor invitation ...
            </Col>
          </Row>
        ) : (

          <Fragment>
            {
              (invitationCode && !invitation && !isLoadingInvitation) &&
              <Alert variant="warning">
                <Alert.Heading>Invitation not found</Alert.Heading>
                <p>
                  We couldn&apos;t find your invitation. Please ensure you copied the
                  signup link in your email correctly. You may also create an account now
                  and ask your Group administrator to invite you later.
                </p>
              </Alert>
            }

            {
              invitation &&
              <Alert variant="info">
                <Alert.Heading>Invitation found</Alert.Heading>
                <p>
                  We found your invitation to the Group
                  &lsquo;{invitation.group.name}&rsquo;.
                  Please choose a password to complete your account creation.
                </p>
              </Alert>
            }

            <RegistrationForm
              handleSubmit={handleSubmit}
              errorMessages={errorMessages}
              items={items}
              invitation={invitation}
            />
          </Fragment>
        )
      }
      </div>
    </RegistrationLoginContainer>
  );
}

export default Register;