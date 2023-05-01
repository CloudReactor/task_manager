import _ from 'lodash';
import { Inflectors } from "en-inflectors";

import React, { useState } from 'react';

import {
  Button,
  Modal,
  ModalBody,
  ModalFooter,
  ModalTitle
} from "react-bootstrap";

import { ModalProps } from 'react-bootstrap/Modal';

import { InstanceProps } from 'react-modal-promise';

import {
  BootstrapButtonVariant
} from '../../types/ui_types';


type Props = ModalProps & InstanceProps<boolean> & {
  disabled?: boolean;
  title: string;
  confirmLabel?: any;
  confirmButtonVariant?: BootstrapButtonVariant;
  faIconName?: string;
  submittingFaIconName?: string;
  submittingLabel?: string;
  cancelLabel?: any;
  cancelButtonVariant?: BootstrapButtonVariant;
  children?: React.ReactElement;
}

// Properties in props but that shouldn't be passed to Modal
const EXTRA_PROPS = [
  'disabled', 'title',
  'confirmLabel', 'confirmButtonVariant',
  'faIconName',
  'submittingFaIconName', 'submittingLabel',
  'cancelLabel', 'cancelButtonVariant',

  // From react-modal-promise
  'isOpen', 'enterTimeout', 'exitTimeout',
  'instanceId', 'onResolve', 'onReject',
  // From react-modal-promise (deprecated)
  'open', 'close',
];

export default function AsyncConfirmationModal(props: Props) {
  const {
    isOpen,
    onResolve,
    size,
    backdrop,
    disabled,
    title,
    confirmLabel,
    confirmButtonVariant,
    faIconName,
    cancelLabel,
    cancelButtonVariant,
    submittingFaIconName,
    submittingLabel,
    children
  } = props;

  const resolvedSize = size || 'lg';
  const resolvedBackdrop = backdrop || 'static';

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
    <Modal {... _.omit(props, EXTRA_PROPS)} show={isOpen} size={resolvedSize}
     backdrop={resolvedBackdrop} onHide={() => onResolve(false)}>
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
