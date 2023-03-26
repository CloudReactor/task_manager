

import {
  AlertMethod
} from '../../../types/domain_types';

import {
  fetchAlertMethod,
  cloneAlertMethod,
  deleteAlertMethod
} from '../../../utils/api';

import React from 'react';
import { withRouter } from 'react-router';

import { EntityDetail, EntityDetailProps } from '../../../components/common/EntityDetail'

import abortableHoc from '../../../hocs/abortableHoc';
import AlertMethodEditor from '../../../components/AlertMethodEditor/index';

class AlertMethodDetail extends EntityDetail<AlertMethod> {
  constructor(props: EntityDetailProps) {
    super(props, 'Alert Method');
  }

  fetchEntity(uuid: string, abortSignal: AbortSignal): Promise<AlertMethod> {
    return fetchAlertMethod(uuid, abortSignal);
  }

  cloneEntity(uuid: string, values: any, abortSignal: AbortSignal): Promise<AlertMethod> {
    return cloneAlertMethod(uuid, values, abortSignal);
  }

  deleteEntity(uuid: string, abortSignal: AbortSignal): Promise<void> {
    return deleteAlertMethod(uuid, abortSignal);
  }

  renderEntity() {
    const {
      entity
    } = this.state;
    return (
      <AlertMethodEditor alertMethod={entity}
        onSaveStarted={this.handleSaveStarted}
        onSaveSuccess={this.handleSaveSuccess}
        onSaveError={this.handleSaveError} />
    );
  }
}

export default withRouter(abortableHoc(AlertMethodDetail));
