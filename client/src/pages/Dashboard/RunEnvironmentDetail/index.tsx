import { CancelToken } from 'axios';

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

import cancelTokenHoc from '../../../hocs/cancelTokenHoc';
import RunEnvironmentEditor from '../../../components/RunEnvironmentEditor';

class RunEnvironmentDetail extends EntityDetail<RunEnvironment> {
  constructor(props: EntityDetailProps) {
    super(props, 'Run Environment');
  }

  fetchEntity(uuid: string, cancelToken: CancelToken): Promise<RunEnvironment> {
    return fetchRunEnvironment(uuid, cancelToken);
  }

  cloneEntity(uuid: string, values: any, cancelToken: CancelToken): Promise<RunEnvironment> {
    return cloneRunEnvironment(uuid, values, cancelToken);
  }

  deleteEntity(uuid: string, cancelToken: CancelToken): Promise<void> {
    return deleteRunEnvironment(uuid, cancelToken);
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

export default withRouter(cancelTokenHoc(RunEnvironmentDetail));
