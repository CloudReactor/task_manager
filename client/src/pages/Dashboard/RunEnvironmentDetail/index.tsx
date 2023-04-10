import {
  RunEnvironment
} from '../../../types/domain_types';

import {
  fetchRunEnvironment,
  cloneRunEnvironment,
  deleteRunEnvironment
} from '../../../utils/api';

import React from 'react';

import { makeEntityDetailComponent, EntityDetailProps } from '../../../components/common/EntityDetailHoc'

import abortableHoc from '../../../hocs/abortableHoc';
import RunEnvironmentEditor from '../../../components/RunEnvironmentEditor';

const RunEnvironmentDetail = makeEntityDetailComponent<RunEnvironment>(
  (props: EntityDetailProps<RunEnvironment>) => {
    return (
      <RunEnvironmentEditor runEnvironment={props.entity ?? undefined}
        onSaveStarted={props.onSaveStarted}
        onSaveSuccess={props.onSaveSuccess}
        onSaveError={props.onSaveError} />
    );


  }, {
    entityName: 'Run Environment',
    fetchEntity: (uuid: string, abortSignal: AbortSignal): Promise<RunEnvironment> => {
      return fetchRunEnvironment(uuid, abortSignal);
    },

    cloneEntity: (uuid: string, values: any, abortSignal: AbortSignal): Promise<RunEnvironment> => {
      return cloneRunEnvironment(uuid, values, abortSignal);
    },

    deleteEntity: (uuid: string, abortSignal: AbortSignal): Promise<void> => {
      return deleteRunEnvironment(uuid, abortSignal);
    }
  }
);

export default abortableHoc(RunEnvironmentDetail);
