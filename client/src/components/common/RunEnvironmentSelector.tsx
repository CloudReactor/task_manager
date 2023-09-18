import { RunEnvironment } from '../../types/domain_types';
import { fetchRunEnvironments } from '../../utils/api';
import abortableHoc, { AbortSignalProps } from '../../hocs/abortableHoc';

import React, { Component } from 'react';
import Form from 'react-bootstrap/Form'

import {
  GlobalContext,
} from '../../context/GlobalContext';

interface Props {
  selectedUuid?: string | null;
  groupId?: number;
  onChange?: (uuid: string | null) => void;
  name?: string;
  noSelectionText?: string;
}

type InnerProps = Props & AbortSignalProps;

interface State {
  selectedUuid?: string | null;
  runEnvironments: RunEnvironment[];
}

class RunEnvironmentSelector extends Component<InnerProps, State> {
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      selectedUuid: props.selectedUuid,
      runEnvironments: []
    }
  }

  async componentDidMount() {
    await this.loadData();
  }

  async componentDidUpdate(prevProps: InnerProps) {
     if (prevProps.groupId !== this.props.groupId) {
       await this.loadData();
     }
   }

  public render() {
    const {
      name,
      noSelectionText
    } = this.props;

    const {
      selectedUuid,
      runEnvironments
    } = this.state;

    return (
      <Form.Control
        as="select"
        name={name || 'run_environment'}
        value={selectedUuid || ''}
        onChange={this.handleChange}
      >
      <option key="empty" value="">
        { noSelectionText || 'Select a Run Environment ...' }
      </option>
      {
        runEnvironments.map(runEnv => {
          return (
            <option key={runEnv.uuid} value={runEnv.uuid} label={runEnv.name}>{runEnv.name}</option>
          );
        })
      }
      </Form.Control>
    );
  }

  handleChange = (event: any) => {
    let uuid = event.target.value;

    if (!uuid) {
      uuid = null;
    }

    this.setState({
      selectedUuid: uuid
    });

    const {
      onChange
    } = this.props;

    if (onChange) {
      onChange(uuid);
    }
  }

  async loadData() {
    const {
      abortSignal
    } = this.props;

    let {

      groupId
    } = this.props;

    const {
      currentGroup
    } = this.context;

    groupId = groupId ?? currentGroup?.id;

    if (!groupId) {
      return;
    }

    const page = await fetchRunEnvironments({
      groupId,
      abortSignal
    });
    const runEnvironments = page.results;

    this.setState({
      runEnvironments
    });
  }
}

export default abortableHoc(RunEnvironmentSelector);