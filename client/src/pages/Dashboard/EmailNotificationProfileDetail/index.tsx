

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

import abortableHoc from '../../../hocs/abortableHoc';
import EmailNotificationProfileEditor from '../../../components/EmailProfileNotificationEditor';

class EmailNotificationProfileDetail extends EntityDetail<EmailNotificationProfile> {
  constructor(props: EntityDetailProps) {
    super(props, 'Email Notification Profile');
  }

  fetchEntity(uuid: string, abortSignal: AbortSignal): Promise<EmailNotificationProfile> {
    return fetchEmailNotificationProfile(uuid, abortSignal);
  }

  cloneEntity(uuid: string, values: any, abortSignal: AbortSignal): Promise<EmailNotificationProfile> {
    return cloneEmailNotificationProfile(uuid, values, abortSignal);
  }

  deleteEntity(uuid: string, abortSignal: AbortSignal): Promise<void> {
    return deleteEmailNotificationProfile(uuid, abortSignal);
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

export default withRouter(abortableHoc(EmailNotificationProfileDetail));
