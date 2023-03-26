

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

import abortableHoc from '../../../hocs/abortableHoc';
import PagerDutyProfileEditor from '../../../components/PagerDutyProfileEditor';

class PagerDutyProfileDetail extends EntityDetail<PagerDutyProfile> {
  constructor(props: EntityDetailProps) {
    super(props, 'PagerDuty Profile');
  }

  fetchEntity(uuid: string, abortSignal: AbortSignal): Promise<PagerDutyProfile> {
    return fetchPagerDutyProfile(uuid, abortSignal);
  }

  cloneEntity(uuid: string, values: any, abortSignal: AbortSignal): Promise<PagerDutyProfile> {
    return clonePagerDutyProfile(uuid, values, abortSignal);
  }

  deleteEntity(uuid: string, abortSignal: AbortSignal): Promise<void> {
    return deletePagerDutyProfile(uuid, abortSignal);
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

export default withRouter(abortableHoc(PagerDutyProfileDetail));
