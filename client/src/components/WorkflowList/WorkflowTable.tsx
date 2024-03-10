import React, { Component, Fragment } from 'react';

import { RunEnvironment, WorkflowSummary } from '../../types/domain_types';
import { ResultsPage } from '../../utils/api';

import "../../styles/tableStyles.scss";


import {
  Form,
  Table
} from 'react-bootstrap'

import RunEnvironmentSelector from "../common/RunEnvironmentSelector/RunEnvironmentSelector";
import WorkflowTableHeader from "./WorkflowTableHeader";
import WorkflowTableBody from "./WorkflowTableBody";
import styles from './WorkflowTable.module.scss';

interface Props {
  q: string | undefined;
  sortBy: string;
  descending: boolean;
  workflowPage: ResultsPage<WorkflowSummary>;
  currentPage: number;
  rowsPerPage: number;
  handleSortChanged: (ordering?: string, toggleDirection?: boolean) => Promise<void>;
  handleSelectedRunEnvironmentUuidsChanged: (uuids?: string[]) => void;
  handleQueryChanged: (event: React.ChangeEvent<HTMLInputElement>) => void;
  loadWorkflows: (
    ordering?: string,
    toggleDirection?: boolean
  ) => Promise<void>;
  handlePageChanged: (currentPage: number) => void;
  handleSelectItemsPerPage: (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => void;
  handleDeletionRequest: (workflow: WorkflowSummary) => void;
  handleEditRequest: (workflow: WorkflowSummary, data: any) => Promise<void>;
  handleStartRequest: (workflow: WorkflowSummary) => Promise<void>;
  handleStopRequest: (workflow: WorkflowSummary) => Promise<void>;
  runEnvironments: RunEnvironment[];
  selectedRunEnvironmentUuids?: string[];
}

const WorkflowTable = (props: Props) => {
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
        </Form>
      </div>

      <div className={styles.searchContainer}>
        <Form.Control
          type="text"
          onChange={props.handleQueryChanged}
          onKeyDown={(keyEvent: any) => {
            if (keyEvent.key === 'Enter') {
              props.loadWorkflows();
            }
          }}
          placeholder="Search Workflows"
          value={q}
        />
      </div>
      {
        (props.workflowPage.count > 0) ? (
          <Table striped bordered responsive hover size="sm">
            <WorkflowTableHeader
              handleSort={props.handleSortChanged}
              sortBy={props.sortBy}
              descending={props.descending}
            />
            <WorkflowTableBody
              workflowPage={props.workflowPage.results}
              handleEditRequest={props.handleEditRequest}
              handleDeletionRequest={props.handleDeletionRequest}
              handleStartRequest={props.handleStartRequest}
              handleStopRequest={props.handleStopRequest}
            />
          </Table>
        ) : (
          <p className="mt-3">
            {
              (q || props.selectedRunEnvironmentUuids) ?
              'No matching Workflows found. Try adjusting your filters.' :
              'No Workflows have been created yet.'
            }
          </p>
        )
      }
    </Fragment>
  );
};

export default WorkflowTable;