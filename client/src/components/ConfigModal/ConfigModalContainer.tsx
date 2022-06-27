import React from 'react';
import {
  Modal,
  ModalTitle
} from 'react-bootstrap';

interface Props {
  isOpen: boolean;
  handleClose: () => void;
  children: any;
  title: string;
}

const ConfigModalContainer = ({isOpen, handleClose, title, children}: Props) => {

  return (
    <Modal
      centered
      show={isOpen}
      onHide={() => handleClose()}
      size="lg"
    >
      <Modal.Header closeButton>
        <ModalTitle>{title}</ModalTitle>
      </Modal.Header>
      <hr className="p-0 m-0"/>
      {children}
    </Modal>
  );
}

export default ConfigModalContainer;