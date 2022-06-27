import _ from 'lodash';
import { Inflectors } from "en-inflectors";

import React, { useState } from 'react';

import {
  Button,
  Modal,
  ModalBody,
  ModalFooter,
  ModalTitle,
  ModalProps
} from "react-bootstrap";

import {
  BootstrapButtonVariant
} from '../../types/ui_types';

interface Props extends ModalProps {
  onResolve: (proceed: boolean) => void,
  disabled?: boolean;
  title: string;
  confirmLabel?: any;
  confirmButtonVariant?: BootstrapButtonVariant;
  faIconName?: string;
  submittingFaIconName?: string;
  submittingLabel?: string;
  cancelLabel?: any;
  cancelButtonVariant?: BootstrapButtonVariant;
}

// Properties in props but that shouldn't be passed to Modal
const EXTRA_PROPS = [
  'onResolve', 'disabled', 'title',
  'confirmLabel', 'confirmButtonVariant',
  'faIconName',
  'submittingFaIconName', 'submittingLabel',
  'cancelLabel', 'cancelButtonVariant',

  // From react-modal-promise
  'isOpen', 'close', 'enterTimeout', 'exitTimeout',
];

export default function AsyncConfirmationModal(props: Props) {
  const {
    isOpen,
    disabled,
    title,
    confirmLabel,
    confirmButtonVariant,
    faIconName,
    cancelLabel,
    cancelButtonVariant,
    submittingFaIconName,
    submittingLabel,
    onResolve,
    children
  } = props;

  // Set defaults
  let {
    size,
    backdrop
  } = props;

  size = size || 'lg';

  if (backdrop === undefined) {
    backdrop = 'static'
  }

  const [isSubmitting, setSubmitting] = useState(false);

  const iconName = isSubmitting ?
    ((submittingFaIconName || 'circle-notch') + ' fa-spin') :
    faIconName;

  const label = isSubmitting ?
    (submittingLabel ||
     (confirmLabel ? new Inflectors(confirmLabel).toGerund() : 'Submitting ...')) :
    (confirmLabel || 'OK');

  const submitForm = async () => {
    setSubmitting(true);

    try {
      onResolve(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal {... _.omit(props, EXTRA_PROPS)} show={isOpen} size={size}
     backdrop={backdrop} onHide={() => onResolve(false)}>
      <Modal.Header closeButton>
        <ModalTitle>{title}</ModalTitle>
      </Modal.Header>

      <ModalBody>
        {children}
      </ModalBody>

      <ModalFooter>
        <Button variant={confirmButtonVariant || 'outline-light'}
          disabled={isSubmitting || disabled || false}
          onClick={submitForm}>
          { iconName && <i className={'fas fa-' + iconName + ' pl-1 pr-1'} /> }
          { label }
        </Button>
        <Button variant={cancelButtonVariant || 'outline-secondary'}
          disabled={isSubmitting || disabled || false}
          onClick={() => onResolve(false)}>
          { cancelLabel || 'Cancel' }
        </Button>
      </ModalFooter>
    </Modal>
  );
}
