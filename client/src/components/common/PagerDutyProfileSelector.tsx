import { isCancel } from 'axios';

import { PagerDutyProfile } from '../../types/domain_types';
import { fetchPagerDutyProfiles } from '../../utils/api';

import React, { Component, Fragment } from 'react';
import Form from 'react-bootstrap/Form'

import { GlobalContext } from '../../context/GlobalContext';
import abortableHoc, { AbortSignalProps } from '../../hocs/abortableHoc';

interface Props {
  selectedPagerDutyProfile?: string | null;
  changedPagerDutyProfile: (uuid: string) => void;
  runEnvironmentUuid?: string;
}

interface State {
  selectedPagerDutyProfile?: string | null;
  pagerDutyProfiles: PagerDutyProfile[];
}

type InnerProps = Props & AbortSignalProps;

class PagerDutyProfileSelector extends Component<InnerProps, State> {
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      selectedPagerDutyProfile: props.selectedPagerDutyProfile,
      pagerDutyProfiles: []
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
      selectedPagerDutyProfile,
      pagerDutyProfiles
    } = this.state;

    return (
      <Fragment>
        <Form.Control
          as="select"
          name="pager_duty_profile"
          value={selectedPagerDutyProfile || ''}
          onChange={this.handleChange}
        >
        <option key="empty" value="">Select a PagerDuty profile</option>
        {
          pagerDutyProfiles.map(pdp => {
            return (
              <option key={pdp.uuid} value={pdp.uuid} label={pdp.name}>{pdp.name}</option>
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
      selectedPagerDutyProfile: uuid
    });

    this.props.changedPagerDutyProfile(uuid);
  }

  async loadData() {
    const { abortSignal, runEnvironmentUuid } = this.props;
    const { currentGroup } = this.context;
    let pagerDutyProfiles: PagerDutyProfile[] = [];

    try {
      const page = await fetchPagerDutyProfiles({
        groupId: currentGroup?.id,
        optionalRunEnvironmentUuid: runEnvironmentUuid,
        abortSignal
      });
      pagerDutyProfiles = page.results;

      this.setState({
        pagerDutyProfiles
      });
    } catch (error) {
      if (isCancel(error)) {
        console.log("Request canceled: " + error.message);
        return;
      }
    }
  }
}


export default abortableHoc(PagerDutyProfileSelector);