import {
  NotificationDeliveryMethod
} from '../../../types/domain_types';

import {
  fetchNotificationDeliveryMethod,
  cloneNotificationDeliveryMethod,
  deleteNotificationDeliveryMethod,
  sendTestEventToNotificationDeliveryMethod
} from '../../../utils/api';

import React, { useState } from 'react';

import { makeEntityDetailComponent, EntityDetailInnerProps } from '../../../components/common/EntityDetailHoc'

import NotificationDeliveryMethodEditor from '../../../components/NotificationDeliveryMethodEditor/index';
import ActionButton from '../../../components/common/ActionButton';
import { BootstrapVariant } from '../../../types/ui_types';

interface Props {
}

const TestEventButton = ({
  entity,
  isFormDirty,
  onFlash,
}: {
  entity: NotificationDeliveryMethod | null;
  isFormDirty: boolean;
  onFlash: (body: React.ReactNode, variant: BootstrapVariant) => void;
}) => {
  const [isTesting, setIsTesting] = useState(false);

  const handleTestEvent = async (_action: string | undefined, _cbData: any) => {
    if (!entity?.uuid) return;
    setIsTesting(true);
    try {
      await sendTestEventToNotificationDeliveryMethod(entity.uuid);
      onFlash('Test event sent successfully.', 'success');
    } catch (ex: any) {
      const msg = ex?.response?.data?.error ?? ex?.message ?? 'Failed to send test event.';
      onFlash(msg, 'danger');
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <ActionButton
      faIconName="paper-plane"
      label="Send Test Event"
      disabled={!entity?.uuid || isTesting || isFormDirty}
      inProgress={isTesting}
      inProgressLabel="Sending..."
      onActionRequested={handleTestEvent}
    />
  );
};

const NotificationDeliveryMethodDetail = makeEntityDetailComponent<NotificationDeliveryMethod, Props>(
  (props: EntityDetailInnerProps<NotificationDeliveryMethod>) => {
    return (
      <NotificationDeliveryMethodEditor notificationDeliveryMethod={props.entity ?? undefined}
        onSaveStarted={props.onSaveStarted}
        onSaveSuccess={props.onSaveSuccess}
        onSaveError={props.onSaveError}
        onDirtyChanged={props.onDirtyChanged}
        onCancelRequested={props.onCancelRequested} />
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
    ),
    navigateToListOnSave: false,
    extraToolbarActions: TestEventButton,
  }
);

export default NotificationDeliveryMethodDetail;
