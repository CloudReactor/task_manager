import {
  AlertMethod
} from '../../../types/domain_types';

import {
  fetchAlertMethod,
  cloneAlertMethod,
  deleteAlertMethod
} from '../../../utils/api';

import React from 'react';

import { makeEntityDetailComponent, EntityDetailInnerProps } from '../../../components/common/EntityDetailHoc'

import AlertMethodEditor from '../../../components/AlertMethodEditor/index';

const AlertMethodDetail = makeEntityDetailComponent<AlertMethod, EntityDetailInnerProps<AlertMethod>>(
  (props: EntityDetailInnerProps<AlertMethod>) => {
    return (
      <AlertMethodEditor alertMethod={props.entity ?? undefined}
        onSaveStarted={props.onSaveStarted}
        onSaveSuccess={props.onSaveSuccess}
        onSaveError={props.onSaveError} />
    );
  }, {
    entityName: 'Alert Method',
    fetchEntity: fetchAlertMethod,
    cloneEntity: cloneAlertMethod,
    deleteEntity: deleteAlertMethod
  }
);

export default AlertMethodDetail;
