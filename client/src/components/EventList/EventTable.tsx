import React, { Fragment } from 'react';

import { Event, RunEnvironment } from '../../types/domain_types';
import { ResultsPage } from '../../utils/api';

import "../../styles/tableStyles.scss";

import {
  Form,
  Table
} from 'react-bootstrap'

import RunEnvironmentSelector from "../common/RunEnvironmentSelector/RunEnvironmentSelector";
import EventTableHeader from "./EventTableHeader";
import EventTableBody from "./EventTableBody";
import styles from './EventTable.module.scss';

interface Props {
  q: string | undefined;
  sortBy: string;
  descending: boolean;
  eventPage: ResultsPage<Event>;
  currentPage: number;
  rowsPerPage: number;
  runEnvironments: RunEnvironment[];
  selectedRunEnvironmentUuids?: string[];
  handleSortChanged: (ordering?: string, toggleDirection?: boolean) => Promise<void>;
  handleSelectedRunEnvironmentUuidsChanged: (uuids?: string[]) => void;
  handleQueryChanged: (event: React.ChangeEvent<HTMLInputElement>) => void;
  loadEvents: (
    ordering?: string,
    toggleDirection?: boolean
  ) => Promise<void>;
  handlePageChanged: (currentPage: number) => void;
  handleSelectItemsPerPage: (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => void;
}

const EventTable = (props: Props) => {
  const {
    q
  } = props;

  return (
    <Fragment>
      <div>
        <Form inline>
          <Form.Group>
            <Form.Label className="mr-3">Run Environment:</Form.Label>
            <RunEnvironmentSelector
              runEnvironments={props.runEnvironments}
              selectedRunEnvironmentUuids={props.selectedRunEnvironmentUuids}
              handleSelectedRunEnvironmentUuidsChanged={props.handleSelectedRunEnvironmentUuidsChanged} />
          </Form.Group>
          <Form.Group className="ml-auto">
            <Form.Control
              type="search"
              placeholder="Search"
              value={q || ''}
              onChange={props.handleQueryChanged}
            />
          </Form.Group>
        </Form>
      </div>

      <Table striped bordered hover className={styles.table}>
        <EventTableHeader
          sortBy={props.sortBy}
          descending={props.descending}
          onSortChanged={props.handleSortChanged}
        />
        <EventTableBody
          eventPage={props.eventPage}
          currentPage={props.currentPage}
          rowsPerPage={props.rowsPerPage}
          handlePageChanged={props.handlePageChanged}
          handleSelectItemsPerPage={props.handleSelectItemsPerPage}
        />
      </Table>
    </Fragment>
  );
};

export default EventTable;
