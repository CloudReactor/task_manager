import axios, { isCancel } from 'axios';

import { EmailNotificationProfile } from '../../types/domain_types';
import { fetchEmailNotificationProfiles } from '../../utils/api';

import React, { Fragment } from 'react';
import Form from 'react-bootstrap/Form'

import { GlobalContext } from '../../context/GlobalContext';
import abortableHoc, { AbortSignalProps } from '../../hocs/abortableHoc';


interface Props {
  selectedEmailNotificationProfile?: string;
  changedEmailNotificationProfile: (uuid: string) => void;
  runEnvironmentUuid?: string;
}

type InnerProps = Props & AbortSignalProps;

interface State {
  selectedEmailNotificationProfile: string | undefined;
  emailNotificationProfiles: EmailNotificationProfile[];
}

class EmailNotificationProfileSelector extends React.Component<InnerProps, State> {
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      selectedEmailNotificationProfile: props.selectedEmailNotificationProfile,
      emailNotificationProfiles: []
    }
  }

  async componentDidMount() {
    await this.loadData();
  }

  async componentDidUpdate(prevProps: InnerProps) {
    if (prevProps.runEnvironmentUuid !== this.props.runEnvironmentUuid) {
      await this.loadData();
    }
  }

  public render() {
    const {
      selectedEmailNotificationProfile,
      emailNotificationProfiles
    } = this.state;

    return (
      <Fragment>
        <Form.Control
          as="select"
          name="email_notification_profile"
          value={selectedEmailNotificationProfile || ''}
          onChange={this.handleChange}
        >
        <option key="empty" value="">Select a Email Notification profile</option>
        {
          emailNotificationProfiles.map(enp => {
            return (
              <option key={enp.uuid} value={enp.uuid} label={enp.name}>{enp.name}</option>
            );
          })
        }
        </Form.Control>
      </Fragment>
    );
  }

  handleChange = (event: any) => {
    const uuid = event.target.value;

    this.setState({
      selectedEmailNotificationProfile: uuid
    });

    this.props.changedEmailNotificationProfile(uuid);
  }

  async loadData() {
    const { abortSignal, runEnvironmentUuid } = this.props;
    const { currentGroup } = this.context;

    try {
      const page = await fetchEmailNotificationProfiles({
        groupId: currentGroup?.id,
        runEnvironmentUuid,
        abortSignal
      });
      const emailNotificationProfiles = page.results;

      this.setState({
        emailNotificationProfiles
      });
    } catch (error) {
      if (isCancel(error)) {
        console.log("Request cancelled: " + error.message);
        return;
      }
    }
  }
}

export default abortableHoc(EmailNotificationProfileSelector);