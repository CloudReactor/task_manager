import _ from 'lodash';

import React, { Component } from 'react';

import {
  NotificationDeliveryMethod
} from '../../types/domain_types';

import { GlobalContext } from '../../context/GlobalContext';
import abortableHoc, { AbortSignalProps } from '../../hocs/abortableHoc';

import { isCancel } from 'axios';

import {
  fetchNotificationDeliveryMethods
} from '../../utils/api';

import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormGroup from '@mui/material/FormGroup';

interface Props {
  entityTypeLabel: string;
  noNotificationDeliveryMethodsText?: string;
  runEnvironmentUuid?: string | null;
  selectedNotificationDeliveryMethodUuids: string[];
  onSelectedNotificationDeliveryMethodsChanged: (methods: NotificationDeliveryMethod[]) => void;
}

type InnerProps = Props & AbortSignalProps;

interface State {
  selectedNotificationDeliveryMethodUuids: string[];
  notificationDeliveryMethods: NotificationDeliveryMethod[];
  uuidsToNotificationDeliveryMethods: any;
}

class NotificationDeliveryMethodSelector extends Component<InnerProps, State> {
  context: any;
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      selectedNotificationDeliveryMethodUuids: props.selectedNotificationDeliveryMethodUuids,
      notificationDeliveryMethods: [],
      uuidsToNotificationDeliveryMethods: {}
    }
  }

  async componentDidMount() {
    await this.loadData();
  }

  componentDidUpdate(prevProps: any) {
    if (prevProps.runEnvironmentUuid !== this.props.runEnvironmentUuid ||
        !_.isEqual(prevProps.selectedNotificationDeliveryMethodUuids, this.props.selectedNotificationDeliveryMethodUuids)) {
      if (prevProps.runEnvironmentUuid !== this.props.runEnvironmentUuid) {
        this.loadData();
      } else {
        this.setState({
          selectedNotificationDeliveryMethodUuids: this.props.selectedNotificationDeliveryMethodUuids
        });
      }
    }
  }

  public render() {
    const {
      runEnvironmentUuid,
      entityTypeLabel,
      noNotificationDeliveryMethodsText
    } = this.props;
    const {
      selectedNotificationDeliveryMethodUuids,
      notificationDeliveryMethods
    } = this.state;

    return (
      (notificationDeliveryMethods.length === 0) ? (noNotificationDeliveryMethodsText ?
        (<p>{noNotificationDeliveryMethodsText}</p>) : (runEnvironmentUuid ? (
          <p>
            No Notification Delivery Methods are available that are scoped to the
            Run Environment of the {entityTypeLabel}.
            To add a Run Environment to the {entityTypeLabel},
            you can either change the scope of a Notification Delivery Method,
            add a new Notification Delivery Method scoped to the Run Environment,
            or remove the Run Environment scope of the {entityTypeLabel}.
          </p>
        ) : (
          <p>
            No Notification Delivery Methods are available.
          </p>
        )
      )) : (
        notificationDeliveryMethods.map(method => {
          return (
            <FormGroup key={method.uuid}>
              <FormControlLabel
                control={
                  <Checkbox
                    color="primary"
                    checked={selectedNotificationDeliveryMethodUuids.indexOf(method.uuid) >= 0}
                    name={method.name}
                    id={method.uuid}
                    value={method.uuid}
                    onChange={this.handleNotificationDeliveryMethodSelected}
                  />
                }
                label={method.name}
              />
            </FormGroup>
          );
        })
      )
    );
  }

  handleNotificationDeliveryMethodSelected = (event: any) => {
    let {
      selectedNotificationDeliveryMethodUuids
    } = this.state;

    const uuid = event.target.value;

    if (selectedNotificationDeliveryMethodUuids.indexOf(uuid) >= 0) {
      selectedNotificationDeliveryMethodUuids = _.without(selectedNotificationDeliveryMethodUuids, uuid);
    } else {
      selectedNotificationDeliveryMethodUuids = selectedNotificationDeliveryMethodUuids.concat([uuid]);
    }

    this.setState({
       selectedNotificationDeliveryMethodUuids
    }, () => {
      const {
        uuidsToNotificationDeliveryMethods
      } = this.state;

      const selectedNotificationDeliveryMethods: NotificationDeliveryMethod[] = [];

      selectedNotificationDeliveryMethodUuids.forEach(uuid => {
        const method = uuidsToNotificationDeliveryMethods[uuid];
        if (method) {
          selectedNotificationDeliveryMethods.push(method as NotificationDeliveryMethod);
        } else {
          console.log(`No Notification Delivery Method found for UUID ${uuid}`);
        }
      });

      this.props.onSelectedNotificationDeliveryMethodsChanged(selectedNotificationDeliveryMethods);
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
    let notificationDeliveryMethods: NotificationDeliveryMethod[] = [];

    while (!done) {
      try {
        const page = await fetchNotificationDeliveryMethods({
          optionalRunEnvironmentUuid: runEnvironmentUuid,
          offset,
          maxResults,
          groupId: currentGroup?.id,
          abortSignal
        });
        notificationDeliveryMethods = notificationDeliveryMethods.concat(page.results);
        done = page.results.length < maxResults;
        offset += maxResults;
      } catch (error) {
        if (isCancel(error)) {
          console.log("Request canceled: " + error.message);
          return;
        }
      }
    }

    const uuidsToNotificationDeliveryMethods: any = {};

    notificationDeliveryMethods.forEach(method => {
      uuidsToNotificationDeliveryMethods[method.uuid] = method;
    });

    this.setState({
      notificationDeliveryMethods,
      uuidsToNotificationDeliveryMethods
    });
  }
}

export default abortableHoc(NotificationDeliveryMethodSelector);
