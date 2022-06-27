import axios from 'axios';

import { PagerDutyProfile } from '../../types/domain_types';
import { fetchPagerDutyProfiles } from '../../utils/api';

import React, { Fragment } from 'react';
import Form from 'react-bootstrap/Form'

import { GlobalContext } from '../../context/GlobalContext';
import cancelTokenHoc, { CancelTokenProps } from '../../hocs/cancelTokenHoc';

interface Props {
  selectedPagerDutyProfile?: string | null;
  changedPagerDutyProfile: (uuid: string) => void;
  runEnvironmentUuid?: string;
}

interface State {
  selectedPagerDutyProfile?: string | null;
  pagerDutyProfiles: PagerDutyProfile[];
}

type InnerProps = Props & CancelTokenProps;

class PagerDutyProfileSelector extends React.Component<InnerProps, State> {
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
    const { cancelToken, runEnvironmentUuid } = this.props;
    const { currentGroup } = this.context;
    let pagerDutyProfiles: PagerDutyProfile[] = [];

    try {
      const page = await fetchPagerDutyProfiles({
        groupId: currentGroup?.id,
        runEnvironmentUuid,
        cancelToken
      });
      pagerDutyProfiles = page.results;

      this.setState({
        pagerDutyProfiles
      });
    } catch (error) {
      if (axios.isCancel(error)) {
        console.log("Request cancelled: " + error.message);
        return;
      }
    }
  }
}


export default cancelTokenHoc(PagerDutyProfileSelector);