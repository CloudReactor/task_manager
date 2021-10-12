import { CancelToken } from 'axios';

import {
  EmailNotificationProfile
} from '../../../types/domain_types';

import {
  fetchEmailNotificationProfile,
  cloneEmailNotificationProfile,
  deleteEmailNotificationProfile
} from '../../../utils/api';

import React from 'react';
import { withRouter } from 'react-router';

import { EntityDetail, EntityDetailProps } from '../../../components/common/EntityDetail'

import cancelTokenHoc from '../../../hocs/cancelTokenHoc';
import EmailNotificationProfileEditor from '../../../components/EmailProfileNotificationEditor';

class EmailNotificationProfileDetail extends EntityDetail<EmailNotificationProfile> {
  constructor(props: EntityDetailProps) {
    super(props, 'Email Notification Profile');
  }

  fetchEntity(uuid: string, cancelToken: CancelToken): Promise<EmailNotificationProfile> {
    return fetchEmailNotificationProfile(uuid, cancelToken);
  }

  cloneEntity(uuid: string, values: any, cancelToken: CancelToken): Promise<EmailNotificationProfile> {
    return cloneEmailNotificationProfile(uuid, values, cancelToken);
  }

  deleteEntity(uuid: string, cancelToken: CancelToken): Promise<void> {
    return deleteEmailNotificationProfile(uuid, cancelToken);
  }

  renderEntity() {
    const {
      entity
    } = this.state;

    return (
      <EmailNotificationProfileEditor emailNotificationProfile={entity}
        onSaveStarted={this.handleSaveStarted}
        onSaveSuccess={this.handleSaveSuccess}
        onSaveError={this.handleSaveError} />
    );
  }
}

export default withRouter(cancelTokenHoc(EmailNotificationProfileDetail));
