import _ from 'lodash';

import { Group } from '../../types/website_types';
import { fetchCurrentUser } from '../../utils/api';
import cancelTokenHoc, { CancelTokenProps } from '../../hocs/cancelTokenHoc';

import React from 'react';
import Form from 'react-bootstrap/Form'

interface Props {
  selectedGroupId?: number;
  onSelectedGroupIdChanged?: (id?: number) => void;
  [propName: string]: any;
}

type InnerProps = Props & CancelTokenProps;

interface State {
  selectedGroupId?: number;
  groups: Group[];
}

class GroupSelector extends React.Component<InnerProps, State> {
  constructor(props: InnerProps) {
    super(props);

    this.state = {
      selectedGroupId: props.selectedGroupId,
      groups: []
    }
  }

  async componentDidMount() {
    await this.loadData();
  }

  public render() {
    const {
      selectedGroupId,
      groups
    } = this.state;

    return (
      <Form.Control
        {... _.omit(this.props, ['selectedGroupId', 'onSelectedGroupIdChanged','cancelToken'])}
        as="select"
        name="group"
        value={selectedGroupId ?? ''}
        onChange={this.handleChange}
      >
      <option key="empty" value="">Select a Group ...</option>
      {
        groups.map(g => {
          return (
            <option key={g.id} value={g.id} label={g.name}>{g.name}</option>
          );
        })
      }
      </Form.Control>
    );
  }

  handleChange = (event: any) => {
    const id = event.target.value;

    const selectedGroupId = id ? parseInt(id) : undefined;

    this.setSelectedGroupId(selectedGroupId);

    this.setState({
      selectedGroupId: id
    });
  }

  setSelectedGroupId(selectedGroupId?: number) {
    this.setState({
      selectedGroupId
    });

    const {
      onSelectedGroupIdChanged
    } = this.props;

    if (onSelectedGroupIdChanged) {
      onSelectedGroupIdChanged(selectedGroupId);
    }
  }

  async loadData() {
    const {
      cancelToken
    } = this.props;

    const currentUser = await fetchCurrentUser({ cancelToken });
    const groups = currentUser.groups;

    this.setState({
      groups
    });

    if (!this.state.selectedGroupId && (groups.length > 0)) {
      this.setSelectedGroupId(groups[0].id);
    }
  }
}

export default cancelTokenHoc(GroupSelector);