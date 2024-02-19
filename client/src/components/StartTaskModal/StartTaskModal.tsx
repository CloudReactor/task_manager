import { Task } from '../../types/domain_types';

import React, { useState } from 'react';
import { Button, ButtonGroup, ButtonToolbar, Modal } from 'react-bootstrap'

import { InstanceProps } from 'react-modal-promise';

import BootstrapTable from 'react-bootstrap-table-next';
import cellEditFactory from 'react-bootstrap-table2-editor';

import { Formik, Form } from 'formik';

const columns = [{
  dataField: 'id',
  text: 'ID',
  hidden: true
}, {
  dataField: 'name',
  text: 'Name'
}, {
  dataField: 'value',
  text: 'Value'
}];

interface EnvironmentRow {
  id: number;
  name: string;
  value: string;
}

type Props = InstanceProps<any> & {
  task: Task
}

export default function StartTaskModal(props: Props) {
  const { isOpen, onResolve, task } = props;

  const [environmentArray, setEnvironmentArray] = useState(
    [] as EnvironmentRow[]);

  const [selectedEnvironmentRowIndices, setSelectedEnvironmentRowIndices] =
    useState([] as number[]);

  const handleOnSelect = (row: EnvironmentRow, isSelect: boolean) => {
    if (isSelect) {
      setSelectedEnvironmentRowIndices([...selectedEnvironmentRowIndices, row.id])
    } else {
      setSelectedEnvironmentRowIndices(
        selectedEnvironmentRowIndices.filter((x: number) => x !== row.id)
      );
    }
  };

  const handleOnSelectAll = (isSelect: boolean, rows: EnvironmentRow[]) => {
    if (isSelect) {
      const ids = rows.map(r => r.id);
      setSelectedEnvironmentRowIndices(ids);
    } else {
      setSelectedEnvironmentRowIndices([]);
    }
  };

  const removeSelectedEnvironmentRowIndices = () => {
    setEnvironmentArray(environmentArray.filter(row => selectedEnvironmentRowIndices.indexOf(row.id) < 0));
    setSelectedEnvironmentRowIndices([]);
  };

  return (
    <Modal
     show={isOpen}
     onHide={() => onResolve(null)}
     backdrop="static" size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Start Task - {task.name}</Modal.Title>
      </Modal.Header>

      <Formik initialValues={ {} } onSubmit={(values: any, actions: any) => {
          const taskExecutionProps = Object.assign({}, values);

          if (environmentArray.length) {
            const envOverrides: any = {};
            environmentArray.forEach(row => {
              envOverrides[row.name] = row.value;
            });
            taskExecutionProps.environment_variables_overrides = envOverrides;
          }
          onResolve(taskExecutionProps);
        }}>
        {({ errors, status, handleChange, handleBlur, values, touched, submitForm, isSubmitting }) => {
          const selectRow: any = {
            mode: 'checkbox',
            clickToEdit: true,
            selected: selectedEnvironmentRowIndices,
            onSelect: handleOnSelect,
            onSelectAll: handleOnSelectAll
          };

          return (
            <Form>
              <Modal.Body>
                <p>
                Environment variables to override
                </p>

                <BootstrapTable keyField='id' data={ environmentArray } columns={ columns }
                 striped={true} selectRow={selectRow}
                 cellEdit={ cellEditFactory({
                   mode: 'click',
                   blurToSave: true
                  }) } bootstrap4={true} />

                <ButtonToolbar>
                  <ButtonGroup size="sm" className="mr-2">
                    <Button variant="outline-primary" onClick={() => setEnvironmentArray(
                        environmentArray.concat([ {
                          id: environmentArray.length ? (Math.max(...environmentArray.map(row => row.id)) + 1) : 0,
                          name: '',
                          value: ''
                        }]))
                      }>
                      <i className="fa fa-plus" /> Add
                    </Button>
                  </ButtonGroup>

                  <ButtonGroup size="sm" className="mr-2">
                    <Button variant="outline-primary" disabled={selectedEnvironmentRowIndices.length === 0}
                     onClick={removeSelectedEnvironmentRowIndices}>
                      <i className="fa fa-minus" /> Remove
                    </Button>
                  </ButtonGroup>
                </ButtonToolbar>
              </Modal.Body>

              <Modal.Footer>
                <Button variant="outline-light" disabled={isSubmitting}
                 onClick={submitForm}>
                  <i className="fa fa-play" /> Start
                </Button>
                <Button variant="outline-secondary" onClick={() => onResolve(null)}>Cancel</Button>
              </Modal.Footer>
            </Form>
          )
        }}
      </Formik>
    </Modal>
  );
}
