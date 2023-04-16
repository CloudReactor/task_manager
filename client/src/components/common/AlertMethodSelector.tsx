import _ from 'lodash';

import React from 'react';

import {
  AlertMethod
} from '../../types/domain_types';

import { GlobalContext } from '../../context/GlobalContext';
import abortableHoc, { AbortSignalProps } from '../../hocs/abortableHoc';

import { isCancel } from 'axios';

import {
  fetchAlertMethods
} from '../../utils/api';

import Checkbox from '@material-ui/core/Checkbox';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import FormGroup from '@material-ui/core/FormGroup';

interface Props {
  entityTypeLabel: string,
  noAlertMethodsText?: string,
  runEnvironmentUuid?: string | null;
  selectedAlertMethodUuids: string[];
  onSelectedAlertMethodsChanged: (alertMethods: AlertMethod[]) => void;
}

type InnerProps = Props & AbortSignalProps;

interface State {
  selectedAlertMethodUuids: string[];
  alertMethods: AlertMethod[];
  uuidsToAlertMethods: any;
}

class AlertMethodSelector extends React.Component<InnerProps, State> {
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      selectedAlertMethodUuids: props.selectedAlertMethodUuids,
      alertMethods: [],
      uuidsToAlertMethods: {}
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
      noAlertMethodsText
    } = this.props;
    const {
      selectedAlertMethodUuids,
      alertMethods
    } = this.state;

    return (
      (alertMethods.length === 0) ? (noAlertMethodsText ?
        (<p>{noAlertMethodsText}</p>) : (runEnvironmentUuid ? (
          <p>
            No Alert Methods are available that are scoped to the
            Run Environment of the {entityTypeLabel}.
            To add a Run Environment to the {entityTypeLabel},
            you can either change the scope of an Alert Method,
            add a new Alert Method scoped to the Run Environment,
            or remove the Run Environment scope of the {entityTypeLabel}.
          </p>
        ) : (
          <p>
            No Alert Methods are available.
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
                    checked={selectedAlertMethodUuids.indexOf(am.uuid) >= 0}
                    name={am.name}
                    id={am.uuid}
                    value={am.uuid}
                    onChange={this.handleAlertMethodSelected}
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

  handleAlertMethodSelected = (event: any) => {
    let {
      selectedAlertMethodUuids
    } = this.state;

    const uuid = event.target.value;

    if (selectedAlertMethodUuids.indexOf(uuid) >= 0) {
      selectedAlertMethodUuids = _.without(selectedAlertMethodUuids, uuid);
    } else {
      selectedAlertMethodUuids = selectedAlertMethodUuids.concat([uuid]);
    }

    this.setState({
       selectedAlertMethodUuids
    }, () => {
      const {
        uuidsToAlertMethods
      } = this.state;

      const selectedAlertMethods: AlertMethod[] = [];

      selectedAlertMethodUuids.forEach(uuid => {
        const am = uuidsToAlertMethods[uuid];
        if (am) {
          selectedAlertMethods.push(am as AlertMethod);
        } else {
          console.log(`No Alert Method found for UUID ${uuid}`);
        }
      });

      this.props.onSelectedAlertMethodsChanged(selectedAlertMethods);
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
    let alertMethods: AlertMethod[] = [];

    while (!done) {
      try {
        const page = await fetchAlertMethods({
          optionalRunEnvironmentUuid: runEnvironmentUuid,
          offset,
          maxResults,
          groupId: currentGroup?.id,
          abortSignal
        });
        alertMethods = alertMethods.concat(page.results);
        done = page.results.length < maxResults;
        offset += maxResults;
      } catch (error) {
        if (isCancel(error)) {
          console.log("Request canceled: " + error.message);
          return;
        }
      }
    }

    const uuidsToAlertMethods: any = {};

    alertMethods.forEach(am => {
      uuidsToAlertMethods[am.uuid] = am;
    });

    this.setState({
      alertMethods,
      uuidsToAlertMethods
    });
  }
}

// cast as React.Component<Props, State> - this drops AbortSignalProps so as to not
// expose AbortSignalProps as outer props
export default abortableHoc(AlertMethodSelector);