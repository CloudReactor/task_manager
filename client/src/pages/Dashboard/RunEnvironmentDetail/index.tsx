import {
  RunEnvironment
} from '../../../types/domain_types';

import {
  fetchRunEnvironment,
  cloneRunEnvironment,
  deleteRunEnvironment
} from '../../../utils/api';

import React from 'react';

import { makeEntityDetailComponent, EntityDetailInnerProps } from '../../../components/common/EntityDetailHoc'

import RunEnvironmentEditor from '../../../components/RunEnvironmentEditor';

interface Props {
}

const RunEnvironmentDetail = makeEntityDetailComponent<RunEnvironment, Props>(
  (props: EntityDetailInnerProps<RunEnvironment>) => {
    return (
      <RunEnvironmentEditor runEnvironment={props.entity ?? undefined}
        onSaveStarted={props.onSaveStarted}
        onSaveSuccess={props.onSaveSuccess}
        onSaveError={props.onSaveError} />
    );
  }, {
    entityName: 'Run Environment',
    fetchEntity: fetchRunEnvironment,
    cloneEntity: cloneRunEnvironment,
    deleteEntity: deleteRunEnvironment
  }
);

export default RunEnvironmentDetail;
