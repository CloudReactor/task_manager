import { UserRegistration, Invitation } from '../../types/website_types';
import { makeConfiguredClient, exceptionToErrorMessages } from '../../axios_config';

import React, { Component, Fragment } from 'react';

import { withRouter } from 'react-router-dom';

import { RouteComponentProps } from 'react-router';

import { Row, Col, Alert } from 'react-bootstrap'

import items from './registrationFormItems';
import RegistrationLoginContainer from '../../components/RegistrationLogin/RegistrationLoginContainer';
import RegistrationForm from '../../components/RegistrationLogin/RegistrationForm';

import * as path from '../../constants/routes';
import { fetchInvitation } from '../../utils/api';

interface Props extends RouteComponentProps {
}

interface State {
  isLoadingInvitation: boolean;
  invitation?: Invitation | null;
  errorMessages: string[];
}

class Register extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    const params = new URLSearchParams(props.location.search);
    const invitationCode = params.get('invitation_code');

    this.state = {
      isLoadingInvitation: !!invitationCode,
      errorMessages: [] as string[]
    };
  }

  async componentDidMount() {
    const {
      location
    } = this.props;

    const params = new URLSearchParams(location.search);
    const invitationCode = params.get('invitation_code');

    if (invitationCode) {
      const invitation = await fetchInvitation(invitationCode);

      console.log('got invitation');
      console.dir(invitation);

      this.setState({
        isLoadingInvitation: false,
        invitation
      });
    }
  }

  private handleSubmit = async (values: UserRegistration): Promise<void> => {
    const {
      location,
      history
    } = this.props;

    const {
      invitation
    } = this.state;

    this.setState({
      errorMessages: []
    });

    try {
      if (invitation) {
        const params = new URLSearchParams(location.search);
        const confirmation_code = params.get('invitation_code');
        Object.assign(values, { confirmation_code });
        await makeConfiguredClient().post('api/v1/invitations/accept/', values);
        history.replace(path.LOGIN + '?status=activated');
      } else {
        // Use email as username so we don't have to ask user to come up with a username
        const bodyObj = Object.assign(values, { username: values.email });
        await makeConfiguredClient().post('auth/users/', bodyObj);

        history.replace(path.REGISTRATION_PENDING +
          '?email=' + encodeURIComponent(values.email));
      }
    } catch (ex) {
      this.setState({
        errorMessages: exceptionToErrorMessages(ex)
      });
    }
  }

  public render() {
    const {
      isLoadingInvitation,
      invitation
    } = this.state;

    return (
      <RegistrationLoginContainer heading="Create your account">
        {
          isLoadingInvitation ? (
            <Row>
              <Col>
                <i className="fas fa-spin fa-circle-notch" />
                Loading your CloudReactor invitation ...
              </Col>
            </Row>
          ) : (

            <Fragment>
              {
                (invitation === null) &&
                <Alert variant="warning">
                  <Alert.Heading>Invitation not found</Alert.Heading>
                  <p>
                    We couldn't find your invitation. Please ensure you copied the
                    signup link in your email correctly. You may also create an accoount now
                    and ask your Group administrator to invite you later.
                  </p>
                </Alert>
              }

              {
                invitation &&
                <Alert variant="info">
                  <Alert.Heading>Invitation found</Alert.Heading>
                  <p>
                    We found your invitation to the Group '{invitation.group.name}'.
                    Please choose a password to complete your account creation.
                  </p>
                </Alert>
              }

              <RegistrationForm
                handleSubmit={this.handleSubmit}
                errorMessages={this.state.errorMessages}
                items={items}
                invitation={invitation}
              />
            </Fragment>
          )
        }
      </RegistrationLoginContainer>
    );
  }
}


export default withRouter(Register);