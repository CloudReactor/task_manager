import { CancelToken } from 'axios';

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

import cancelTokenHoc from '../../../hocs/cancelTokenHoc';
import AlertMethodEditor from '../../../components/AlertMethodEditor/index';

class AlertMethodDetail extends EntityDetail<AlertMethod> {
  constructor(props: EntityDetailProps) {
    super(props, 'Alert Method');
  }

  fetchEntity(uuid: string, cancelToken: CancelToken): Promise<AlertMethod> {
    return fetchAlertMethod(uuid, cancelToken);
  }

  cloneEntity(uuid: string, values: any, cancelToken: CancelToken): Promise<AlertMethod> {
    return cloneAlertMethod(uuid, values, cancelToken);
  }

  deleteEntity(uuid: string, cancelToken: CancelToken): Promise<void> {
    return deleteAlertMethod(uuid, cancelToken);
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

export default withRouter(cancelTokenHoc(AlertMethodDetail));
