import { makeConfiguredClient, exceptionToErrorMessages } from '../axios_config';

import React, { Component, Fragment } from "react";
import { Alert } from 'react-bootstrap';

import ActionButton from '../components/common/ActionButton';
import RegistrationLoginContainer from '../components/RegistrationLogin/RegistrationLoginContainer';

interface Props {
}

interface State {
  resending: boolean,
  errorMessages: string[],
  successMessage?: string
}

export default class RegistrationPending extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    this.state = {
      resending: false,
      errorMessages: [] as string[]
    };
  }

  public render() {
    const {
      resending,
      errorMessages,
      successMessage
    } = this.state;

    const email = this.extractEmail();

    return (

      <RegistrationLoginContainer heading="Confirm your email">
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
        {
          successMessage &&
          <Alert variant="success">
            { successMessage }
          </Alert>
        }

        <p>
          Thank you for signing up for CloudReactor!
        </p>
        <p>
          Please check your email and click the link in the message to complete signup.
        </p>
        {
          email &&
          <Fragment>
            <hr style={{ width: '75%', backgroundColor: '#aaa', marginTop: '40px', height: '1px', border: 'none' }} />
            <p>
              No activation email? Click the button below to resend it.
            </p>

            <ActionButton action="resend" label="Resend" inProgress={resending}
              color="secondary" size="medium"
              onActionRequested={this.resendEmail}/>
          </Fragment>
        }
      </RegistrationLoginContainer>
    );
  }

  private resendEmail = (action: string | undefined, cbData: any) : any => {
    this.setState({
      resending: true,
      successMessage: undefined
    }, async () => {
      try {
        await makeConfiguredClient().post('auth/users/resend_activation/', {
          email: this.extractEmail()
        });

        this.setState({
          resending: false,
          successMessage: 'Activation email was sent.'
        });
      } catch (ex) {
        this.setState({
          resending: false,
          errorMessages: exceptionToErrorMessages(ex),
          successMessage: undefined
        });
      }
    });
  }

  private extractEmail = () : string | null => {
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    return urlParams.get('email');
  }
}