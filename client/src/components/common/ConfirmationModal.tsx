import React, { Component }  from 'react';

import {
  Button,
  Modal,
  ModalBody,
  ModalFooter,
  ModalTitle
} from "react-bootstrap";

import { BootstrapButtonVariant } from '../../types/ui_types';

interface Props {
  shouldShow: boolean;
  disabled?: boolean;
  title: string;
  body?: any;
  confirmLabel?: any;
  confirmButtonVariant?: BootstrapButtonVariant;
  cancelLabel?: any;
  onConfirm?: (e: any) => void;
  onCancel: (e: any) => void;
}

interface State {
}

class ConfirmationModal extends Component<Props, State> {
  public render() {
    const {
      shouldShow,
      disabled,
      title,
      body,
      confirmLabel,
      confirmButtonVariant,
      cancelLabel,
      onConfirm,
      onCancel
    } = this.props;

    return (
      <Modal centered show={shouldShow} onHide={() => onCancel(null) }>
        <Modal.Header closeButton>
          <ModalTitle>{title}</ModalTitle>
        </Modal.Header>

        <ModalBody>
          { this.props.children || body }
        </ModalBody>

        <ModalFooter>
          <Button variant="secondary" disabled={disabled || false}
                  onClick={onCancel}>{cancelLabel || 'Cancel'}</Button>
          <Button variant={confirmButtonVariant || 'primary'}
                  disabled={disabled || false}
                  onClick={onConfirm}>{confirmLabel || 'OK'}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

export default ConfirmationModal;