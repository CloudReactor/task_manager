import {
  NotificationProfile
} from '../../../types/domain_types';

import {
  fetchNotificationProfile,
  cloneNotificationProfile,
  deleteNotificationProfile
} from '../../../utils/api';

import React from 'react';

import { makeEntityDetailComponent, EntityDetailInnerProps } from '../../../components/common/EntityDetailHoc'

import NotificationProfileEditor from '../../../components/NotificationProfileEditor/index';

interface Props {
}

const NotificationProfileDetail = makeEntityDetailComponent<NotificationProfile, Props>(
  (props: EntityDetailInnerProps<NotificationProfile>) => {
    return (
      <NotificationProfileEditor notificationProfile={props.entity ?? undefined}
        onSaveStarted={props.onSaveStarted}
        onSaveSuccess={props.onSaveSuccess}
        onSaveError={props.onSaveError} />
    );
  }, {
    entityName: 'Notification Profile',
    fetchEntity: fetchNotificationProfile,
    cloneEntity: cloneNotificationProfile,
    deleteEntity: deleteNotificationProfile,
    makeDeletionConfirmationNode: (entity) => (
      <p>
        Are you sure you want to delete the Notification Profile &lsquo;{entity.name}&rsquo;?
        All Tasks and Workflows using this Notification Profile won&apos;t use it anymore.
      </p>
    )
  }
);

export default NotificationProfileDetail;
