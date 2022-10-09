import { makeConfiguredClient, exceptionToErrorMessages } from '../axios_config';

import React, { Component, Fragment } from 'react';
import { RouteComponentProps } from 'react-router';
import { withRouter, Link } from 'react-router-dom';

import {
  Alert,
  Button,
} from 'react-bootstrap';

import RegistrationLoginContainer from '../components/RegistrationLogin/RegistrationLoginContainer';

import * as path from '../constants/routes';
import styles from './registration_activation.module.scss';

interface Props extends RouteComponentProps {
}

interface State {
  activated: boolean,
  errorMessages: string[],
  header: string;
}

class RegistrationActivation extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    this.state = {
      activated: false,
      header: 'Email verified!',
      errorMessages: [] as string[]
    };
  }

  private handleSubmit = async (): Promise<void> => {
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    const uid = urlParams.get('uid');
    const token = urlParams.get('token');

    console.log(`submitted activation for user ${uid}`);

    try {
      await makeConfiguredClient().post(
        'auth/users/activation/', {
          uid,
          token
        });

      this.setState({
        activated: true,
        header: 'Account activated!'
      });
    } catch (ex) {
      this.setState({
        errorMessages: exceptionToErrorMessages(ex)
      });
    }
  }

  public render() {
    const {
      activated,
      errorMessages,
      header,
    } = this.state;

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
                  <Button size="lg" onClick={this.handleSubmit}>Activate</Button>
                </div>
              </Fragment>
            )
          }
        </div>
      </RegistrationLoginContainer>
    );
  }
}

export default withRouter(RegistrationActivation);
