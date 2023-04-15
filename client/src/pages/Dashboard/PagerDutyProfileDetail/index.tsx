

import {
  PagerDutyProfile
} from '../../../types/domain_types';

import {
  fetchPagerDutyProfile,
  clonePagerDutyProfile,
  deletePagerDutyProfile
} from '../../../utils/api';

import React from 'react';

import { makeEntityDetailComponent, EntityDetailInnerProps } from '../../../components/common/EntityDetailHoc'

import PagerDutyProfileEditor from '../../../components/PagerDutyProfileEditor';

interface Props {
}

const PagerDutyProfileDetail = makeEntityDetailComponent<PagerDutyProfile, Props>(
  (props: EntityDetailInnerProps<PagerDutyProfile>) => {
    return (
      <PagerDutyProfileEditor pagerDutyProfile={props.entity ?? undefined}
        onSaveStarted={props.onSaveStarted}
        onSaveSuccess={props.onSaveSuccess}
        onSaveError={props.onSaveError} />
    );
  }, {
    entityName: 'PagerDuty Profile',
    fetchEntity: fetchPagerDutyProfile,
    cloneEntity: clonePagerDutyProfile,
    deleteEntity: deletePagerDutyProfile
  }
);

export default PagerDutyProfileDetail;
