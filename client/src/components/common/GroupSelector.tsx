import _ from 'lodash';

import { Group } from '../../types/website_types';
import { fetchCurrentUser } from '../../utils/api';
import abortableHoc, { AbortSignalProps } from '../../hocs/abortableHoc';

import React, { Component } from 'react';
import Form from 'react-bootstrap/Form'

interface Props {
  selectedGroupId?: number;
  onSelectedGroupIdChanged?: (id?: number) => void;
  [propName: string]: any;
}

type InnerProps = Props & AbortSignalProps;

interface State {
  selectedGroupId?: number;
  groups: Group[];
}

class GroupSelector extends Component<InnerProps, State> {
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
        {... _.omit(this.props, ['selectedGroupId', 'onSelectedGroupIdChanged','abortSignal'])}
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
      abortSignal
    } = this.props;

    const currentUser = await fetchCurrentUser({ abortSignal });
    const groups = currentUser.groups;

    this.setState({
      groups
    });

    if (!this.state.selectedGroupId && (groups.length > 0)) {
      this.setSelectedGroupId(groups[0].id);
    }
  }
}

export default abortableHoc(GroupSelector);