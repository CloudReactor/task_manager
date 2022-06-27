import { CancelToken } from 'axios';

import {
  PagerDutyProfile
} from '../../../types/domain_types';

import {
  fetchPagerDutyProfile,
  clonePagerDutyProfile,
  deletePagerDutyProfile
} from '../../../utils/api';

import React from 'react';
import { withRouter } from 'react-router';

import { EntityDetail, EntityDetailProps } from '../../../components/common/EntityDetail'

import cancelTokenHoc from '../../../hocs/cancelTokenHoc';
import PagerDutyProfileEditor from '../../../components/PagerDutyProfileEditor';

class PagerDutyProfileDetail extends EntityDetail<PagerDutyProfile> {
  constructor(props: EntityDetailProps) {
    super(props, 'PagerDuty Profile');
  }

  fetchEntity(uuid: string, cancelToken: CancelToken): Promise<PagerDutyProfile> {
    return fetchPagerDutyProfile(uuid, cancelToken);
  }

  cloneEntity(uuid: string, values: any, cancelToken: CancelToken): Promise<PagerDutyProfile> {
    return clonePagerDutyProfile(uuid, values, cancelToken);
  }

  deleteEntity(uuid: string, cancelToken: CancelToken): Promise<void> {
    return deletePagerDutyProfile(uuid, cancelToken);
  }

  renderEntity() {
    const {
      entity
    } = this.state;

    return (
      <PagerDutyProfileEditor pagerDutyProfile={entity}
        onSaveStarted={this.handleSaveStarted}
        onSaveSuccess={this.handleSaveSuccess}
        onSaveError={this.handleSaveError} />
    );
  }
}

export default withRouter(cancelTokenHoc(PagerDutyProfileDetail));
