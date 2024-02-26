import _ from 'lodash';

import React, { Component } from 'react';

import {
  NotificationMethod
} from '../../types/domain_types';

import { GlobalContext } from '../../context/GlobalContext';
import abortableHoc, { AbortSignalProps } from '../../hocs/abortableHoc';

import { isCancel } from 'axios';

import {
  fetchNotificationMethods
} from '../../utils/api';

import Checkbox from '@material-ui/core/Checkbox';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import FormGroup from '@material-ui/core/FormGroup';

interface Props {
  entityTypeLabel: string,
  noNotificationMethodsText?: string,
  runEnvironmentUuid?: string | null;
  selectedNotificationMethodUuids: string[];
  onSelectedNotificationMethodsChanged: (alertMethods: NotificationMethod[]) => void;
}

type InnerProps = Props & AbortSignalProps;

interface State {
  selectedNotificationMethodUuids: string[];
  notificationMethods: NotificationMethod[];
  uuidsToNotificationMethods: any;
}

class NotificationMethodSelector extends Component<InnerProps, State> {
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      selectedNotificationMethodUuids: props.selectedNotificationMethodUuids,
      notificationMethods: [],
      uuidsToNotificationMethods: {}
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
      noNotificationMethodsText: noNotificationMethodsText
    } = this.props;
    const {
      selectedNotificationMethodUuids: selectedNotificationMethodUuids,
      notificationMethods: alertMethods
    } = this.state;

    return (
      (alertMethods.length === 0) ? (noNotificationMethodsText ?
        (<p>{noNotificationMethodsText}</p>) : (runEnvironmentUuid ? (
          <p>
            No Notification Methods are available that are scoped to the
            Run Environment of the {entityTypeLabel}.
            To add a Run Environment to the {entityTypeLabel},
            you can either change the scope of a Notification Method,
            add a new Notification Method scoped to the Run Environment,
            or remove the Run Environment scope of the {entityTypeLabel}.
          </p>
        ) : (
          <p>
            No Notification Methods are available.
          </p>
        )
      )) : (
        alertMethods.map(am => {
          return (
            <FormGroup key={am.uuid}>
              <FormControlLabel
                control={
                  <Checkbox
                    color="primary"
                    checked={selectedNotificationMethodUuids.indexOf(am.uuid) >= 0}
                    name={am.name}
                    id={am.uuid}
                    value={am.uuid}
                    onChange={this.handleNotificationMethodSelected}
                  />
                }
                label={am.name}
              />
            </FormGroup>
          );
        })
      )

    );
  }

  handleNotificationMethodSelected = (event: any) => {
    let {
      selectedNotificationMethodUuids: selectedNotificationMethodUuids
    } = this.state;

    const uuid = event.target.value;

    if (selectedNotificationMethodUuids.indexOf(uuid) >= 0) {
      selectedNotificationMethodUuids = _.without(selectedNotificationMethodUuids, uuid);
    } else {
      selectedNotificationMethodUuids = selectedNotificationMethodUuids.concat([uuid]);
    }

    this.setState({
       selectedNotificationMethodUuids: selectedNotificationMethodUuids
    }, () => {
      const {
        uuidsToNotificationMethods
      } = this.state;

      const selectedNotificationMethods: NotificationMethod[] = [];

      selectedNotificationMethodUuids.forEach(uuid => {
        const am = uuidsToNotificationMethods[uuid];
        if (am) {
          selectedNotificationMethods.push(am as NotificationMethod);
        } else {
          console.log(`No Notification Method found for UUID ${uuid}`);
        }
      });

      this.props.onSelectedNotificationMethodsChanged(selectedNotificationMethods);
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
    let notificationMethods: NotificationMethod[] = [];

    while (!done) {
      try {
        const page = await fetchNotificationMethods({
          optionalRunEnvironmentUuid: runEnvironmentUuid,
          offset,
          maxResults,
          groupId: currentGroup?.id,
          abortSignal
        });
        notificationMethods = notificationMethods.concat(page.results);
        done = page.results.length < maxResults;
        offset += maxResults;
      } catch (error) {
        if (isCancel(error)) {
          console.log("Request canceled: " + error.message);
          return;
        }
      }
    }

    const uuidsToNotificationMethods: any = {};

    notificationMethods.forEach(am => {
      uuidsToNotificationMethods[am.uuid] = am;
    });

    this.setState({
      notificationMethods: notificationMethods,
      uuidsToNotificationMethods
    });
  }
}

export default abortableHoc(NotificationMethodSelector);
