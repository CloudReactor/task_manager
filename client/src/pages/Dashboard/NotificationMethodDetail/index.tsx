import {
  NotificationMethod
} from '../../../types/domain_types';

import {
  fetchNotificationMethod,
  cloneNotificationMethod,
  deleteNotificationMethod
} from '../../../utils/api';

import React from 'react';

import { makeEntityDetailComponent, EntityDetailInnerProps } from '../../../components/common/EntityDetailHoc'

import NotificationMethodEditor from '../../../components/NotificationMethodEditor/index';

interface Props {
}

const NotificationMethodDetail = makeEntityDetailComponent<NotificationMethod, Props>(
  (props: EntityDetailInnerProps<NotificationMethod>) => {
    return (
      <NotificationMethodEditor notificationMethod={props.entity ?? undefined}
        onSaveStarted={props.onSaveStarted}
        onSaveSuccess={props.onSaveSuccess}
        onSaveError={props.onSaveError} />
    );
  }, {
    entityName: 'Notification Method',
    fetchEntity: fetchNotificationMethod,
    cloneEntity: cloneNotificationMethod,
    deleteEntity: deleteNotificationMethod
  }
);

export default NotificationMethodDetail;
