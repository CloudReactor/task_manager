
import { IconName } from '@fortawesome/fontawesome-svg-core';

interface Props {
  children?: React.ReactElement;
  shouldShow: boolean;
  disabled?: boolean;
  title: string;
  body?: any;
  confirmLabel?: any;
  confirmButtonVariant?: BootstrapButtonVariant;
  cancelLabel?: any;
  onConfirm?: (e: any) => void;
  onCancel: (e: any) => void;
  confirmIcon?: IconName;
}

import React from 'react';
import {
  Button,
  Modal,
  ModalBody,
  ModalFooter,
  ModalTitle
} from "react-bootstrap";

import { BootstrapButtonVariant } from '../../types/ui_types';

const ConfirmationModal: React.FC<Props> = ({
  children,
  shouldShow,
  disabled,
  title,
  body,
  confirmLabel,
  confirmIcon,
  confirmButtonVariant,
  cancelLabel,
  onConfirm,
  onCancel
}) => {
  return (
    <Modal centered show={shouldShow} onHide={() => onCancel(null)}>
      <Modal.Header closeButton>
        <ModalTitle>{title}</ModalTitle>
      </Modal.Header>

      <ModalBody>
        {children || body}
      </ModalBody>

      <ModalFooter>
        <Button variant="secondary" disabled={disabled ?? false} onClick={onCancel}>
          {cancelLabel ?? 'Cancel'}
        </Button>
        <Button variant={confirmButtonVariant ?? 'primary'}
          disabled={disabled ?? false}
          onClick={onConfirm}>
          {confirmIcon && <i className={'fas fa-' + confirmIcon} />} {confirmLabel ?? 'OK'}
        </Button>
      </ModalFooter>
    </Modal>
  );
};

export default ConfirmationModal;
