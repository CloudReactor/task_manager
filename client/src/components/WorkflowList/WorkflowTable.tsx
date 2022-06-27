import React, { Component, Fragment } from 'react';

import { RunEnvironment, WorkflowSummary } from '../../types/domain_types';
import { ResultsPage } from '../../utils/api';

import "../../styles/tableStyles.scss";


import {
  Form,
  Table
} from 'react-bootstrap'

import WorkflowTableHeader from "./WorkflowTableHeader";
import WorkflowTableBody from "./WorkflowTableBody";
import styles from './WorkflowTable.module.scss';

interface Props {
  q: string;
  sortBy: string;
  descending: boolean;
  workflowPage: ResultsPage<WorkflowSummary>;
  currentPage: number;
  rowsPerPage: number;
  handleSortChanged: (ordering?: string, toggleDirection?: boolean) => Promise<void>;
  handleRunEnvironmentChanged: (event: React.ChangeEvent<HTMLInputElement>) => void;
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
  selectedRunEnvironmentUuid: string;
}

interface State {
}

class WorkflowTable extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {}
  }

  public render() {
    const {
      q,
      sortBy,
      descending,
      workflowPage,
      handleRunEnvironmentChanged,
      handleEditRequest,
      handleDeletionRequest,
      handleSortChanged,
      handleStartRequest,
      handleStopRequest,
      runEnvironments,
      selectedRunEnvironmentUuid
    } = this.props;

    return (
      <Fragment>
        <div>
          <Form inline>
            <Form.Label>Run Environment:</Form.Label>
            <Form.Control
              as="select"
              onChange={handleRunEnvironmentChanged}
              value={selectedRunEnvironmentUuid}
              className={'ml-sm-3 ' + styles.runEnvironmentSelector}
              size="sm"
            >
              <option key="all" value="">Show all</option>
              {
                runEnvironments.map((runEnvironment: any) => {
                  return(
                    <option
                      key={runEnvironment.uuid}
                      value={runEnvironment.uuid}
                    >
                      {runEnvironment.name}
                    </option>
                  );
                })
              }
            </Form.Control>
          </Form>
        </div>

        <div className={styles.searchContainer}>
          <Form.Control
            type="text"
            onChange={this.props.handleQueryChanged}
            onKeyDown={(keyEvent: any) => {
              if (keyEvent.key === 'Enter') {
                this.props.loadWorkflows();
              }
            }}
            placeholder="Search Workflows"
            value={q}
          />
        </div>
        {
          (workflowPage.count > 0) ? (
            <Table striped bordered responsive hover size="sm">
              <WorkflowTableHeader
                handleSort={handleSortChanged}
                sortBy={sortBy}
                descending={descending}
              />
              <WorkflowTableBody
                workflowPage={workflowPage.results}
                handleEditRequest={handleEditRequest}
                handleDeletionRequest={handleDeletionRequest}
                handleStartRequest={handleStartRequest}
                handleStopRequest={handleStopRequest}
              />
            </Table>
          ) : (
            <p className="mt-3">
              {
                (q || selectedRunEnvironmentUuid) ?
                'No matching Workflows found. Try adjusting your filters.' :
                'No Workflows have been created yet.'
              }
            </p>
          )
        }
      </Fragment>
    );
  }
}

export default WorkflowTable;