

import {
  RunEnvironment
} from '../../../types/domain_types';

import {
  fetchRunEnvironment,
  cloneRunEnvironment,
  deleteRunEnvironment
} from '../../../utils/api';

import React from 'react';
import { withRouter } from 'react-router';

import { EntityDetail, EntityDetailProps } from '../../../components/common/EntityDetail'

import abortableHoc from '../../../hocs/abortableHoc';
import RunEnvironmentEditor from '../../../components/RunEnvironmentEditor';

class RunEnvironmentDetail extends EntityDetail<RunEnvironment> {
  constructor(props: EntityDetailProps) {
    super(props, 'Run Environment');
  }

  fetchEntity(uuid: string, abortSignal: AbortSignal): Promise<RunEnvironment> {
    return fetchRunEnvironment(uuid, abortSignal);
  }

  cloneEntity(uuid: string, values: any, abortSignal: AbortSignal): Promise<RunEnvironment> {
    return cloneRunEnvironment(uuid, values, abortSignal);
  }

  deleteEntity(uuid: string, abortSignal: AbortSignal): Promise<void> {
    return deleteRunEnvironment(uuid, abortSignal);
  }

  renderEntity() {
    const {
      entity
    } = this.state;
    return (
      <RunEnvironmentEditor runEnvironment={entity}
        onSaveStarted={this.handleSaveStarted}
        onSaveSuccess={this.handleSaveSuccess}
        onSaveError={this.handleSaveError} />
    );
  }
}

export default withRouter(abortableHoc(RunEnvironmentDetail));
