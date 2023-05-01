import {
  EmailNotificationProfile
} from '../../../types/domain_types';

import {
  fetchEmailNotificationProfile,
  cloneEmailNotificationProfile,
  deleteEmailNotificationProfile
} from '../../../utils/api';

import React from 'react';

import { makeEntityDetailComponent, EntityDetailInnerProps } from '../../../components/common/EntityDetailHoc'

import EmailNotificationProfileEditor from '../../../components/EmailNotificationProfileEditor';

interface Props {
}

const EmailNotificationProfileDetail = makeEntityDetailComponent<EmailNotificationProfile, Props>(
  (props: EntityDetailInnerProps<EmailNotificationProfile>) => {
    return (
      <EmailNotificationProfileEditor emailNotificationProfile={props.entity ?? undefined}
        onSaveStarted={props.onSaveStarted}
        onSaveSuccess={props.onSaveSuccess}
        onSaveError={props.onSaveError} />
    );
  }, {
    entityName: 'Email Notification Profile',
    fetchEntity: fetchEmailNotificationProfile,
    cloneEntity: cloneEmailNotificationProfile,
    deleteEntity: deleteEmailNotificationProfile
  }
);

export default EmailNotificationProfileDetail;
