import {
  NotificationDeliveryMethod
} from '../../../types/domain_types';

import {
  fetchNotificationDeliveryMethod,
  cloneNotificationDeliveryMethod,
  deleteNotificationDeliveryMethod
} from '../../../utils/api';

import React from 'react';

import { makeEntityDetailComponent, EntityDetailInnerProps } from '../../../components/common/EntityDetailHoc'

import NotificationDeliveryMethodEditor from '../../../components/NotificationDeliveryMethodEditor/index';

interface Props {
}

const NotificationDeliveryMethodDetail = makeEntityDetailComponent<NotificationDeliveryMethod, Props>(
  (props: EntityDetailInnerProps<NotificationDeliveryMethod>) => {
    return (
      <NotificationDeliveryMethodEditor notificationDeliveryMethod={props.entity ?? undefined}
        onSaveStarted={props.onSaveStarted}
        onSaveSuccess={props.onSaveSuccess}
        onSaveError={props.onSaveError} />
    );
  }, {
    entityName: 'Notification Delivery Method',
    fetchEntity: fetchNotificationDeliveryMethod,
    cloneEntity: cloneNotificationDeliveryMethod,
    deleteEntity: deleteNotificationDeliveryMethod,
    makeDeletionConfirmationNode: (entity) => (
      <p>
        Are you sure you want to delete the Notification Delivery Method &lsquo;{entity.name}&rsquo;?
        All Notification Profiles using this Notification Delivery Method won&apos;t use
        this Notification Delivery Method anymore.
      </p>
    )
  }
);

export default NotificationDeliveryMethodDetail;
