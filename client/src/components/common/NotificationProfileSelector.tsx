import _ from 'lodash';

import React, { Component } from 'react';

import {
  NotificationProfile
} from '../../types/domain_types';

import { GlobalContext } from '../../context/GlobalContext';
import abortableHoc, { AbortSignalProps } from '../../hocs/abortableHoc';

import { isCancel } from 'axios';

import {
  fetchNotificationProfiles
} from '../../utils/api';

import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormGroup from '@mui/material/FormGroup';

interface Props {
  entityTypeLabel: string,
  noNotificationProfilesText?: string,
  runEnvironmentUuid?: string | null;
  selectedNotificationProfileUuids: string[];
  onSelectedNotificationProfilesChanged: (notificationProfiles: NotificationProfile[]) => void;
}

type InnerProps = Props & AbortSignalProps;

interface State {
  selectedNotificationProfileUuids: string[];
  notificationProfiles: NotificationProfile[];
  uuidsToNotificationProfiles: any;
}

class NotificationProfileSelector extends Component<InnerProps, State> {
  context: any;
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      selectedNotificationProfileUuids: props.selectedNotificationProfileUuids,
      notificationProfiles: [],
      uuidsToNotificationProfiles: {}
    }
  }

  async componentDidMount() {
    await this.loadData();
  }

  componentDidUpdate(prevProps: any) {
    if (prevProps.runEnvironmentUuid !== this.props.runEnvironmentUuid) {
      this.loadData();
    }
  }

  public render() {
    const {
      runEnvironmentUuid,
      entityTypeLabel,
      noNotificationProfilesText
    } = this.props;
    const {
      selectedNotificationProfileUuids,
      notificationProfiles
    } = this.state;

    return (
      (notificationProfiles.length === 0) ? (noNotificationProfilesText ?
        (<p>{noNotificationProfilesText}</p>) : (runEnvironmentUuid ? (
          <p>
            No Notification Profiles are available that are scoped to the
            Run Environment of the {entityTypeLabel}.
            To add a Run Environment to the {entityTypeLabel},
            you can either change the scope of a Notification Profile,
            add a new Notification Profile scoped to the Run Environment,
            or remove the Run Environment scope of the {entityTypeLabel}.
          </p>
        ) : (
          <p>
            No Notification Profiles are available.
          </p>
        )
      )) : (
        notificationProfiles.map(np => {
          return (
            <FormGroup key={np.uuid}>
              <FormControlLabel
                control={
                  <Checkbox
                    color="primary"
                    checked={selectedNotificationProfileUuids.indexOf(np.uuid) >= 0}
                    name={np.name}
                    id={np.uuid}
                    value={np.uuid}
                    onChange={this.handleNotificationProfileSelected}
                  />
                }
                label={np.name}
              />
            </FormGroup>
          );
        })
      )

    );
  }

  handleNotificationProfileSelected = (event: any) => {
    let {
      selectedNotificationProfileUuids
    } = this.state;

    const uuid = event.target.value;

    if (selectedNotificationProfileUuids.indexOf(uuid) >= 0) {
      selectedNotificationProfileUuids = _.without(selectedNotificationProfileUuids, uuid);
    } else {
      selectedNotificationProfileUuids = selectedNotificationProfileUuids.concat([uuid]);
    }

    this.setState({
       selectedNotificationProfileUuids
    }, () => {
      const {
        uuidsToNotificationProfiles
      } = this.state;

      const selectedNotificationProfiles: NotificationProfile[] = [];

      selectedNotificationProfileUuids.forEach(uuid => {
        const np = uuidsToNotificationProfiles[uuid];
        if (np) {
          selectedNotificationProfiles.push(np as NotificationProfile);
        } else {
          console.log(`No Notification Profile found for UUID ${uuid}`);
        }
      });

      this.props.onSelectedNotificationProfilesChanged(selectedNotificationProfiles);
    });
  }

  async loadData() {
    const {
      runEnvironmentUuid,
      abortSignal
    } = this.props;
    const { currentGroup } = this.context;
    const maxResults = 100;
    let offset = 0;
    let done = false;
    let notificationProfiles: NotificationProfile[] = [];

    while (!done) {
      try {
        const page = await fetchNotificationProfiles({
          optionalRunEnvironmentUuid: runEnvironmentUuid,
          offset,
          maxResults,
          groupId: currentGroup?.id,
          abortSignal
        });
        notificationProfiles = notificationProfiles.concat(page.results);
        done = page.results.length < maxResults;
        offset += maxResults;
      } catch (error) {
        if (isCancel(error)) {
          console.log("Request canceled: " + error.message);
          return;
        }
      }
    }

    const uuidsToNotificationProfiles: any = {};

    notificationProfiles.forEach(np => {
      uuidsToNotificationProfiles[np.uuid] = np;
    });

    this.setState({
      notificationProfiles,
      uuidsToNotificationProfiles
    });
  }
}

export default abortableHoc(NotificationProfileSelector);
