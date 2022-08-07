import React, { Fragment } from "react";
import { Table } from "react-bootstrap";

import TablePagination from "@material-ui/core/TablePagination";
import TableHeader from "./Table/TableHeader";
import TableBody from "./Table/TableBody";
import DefaultPagination from "../Pagination/Pagination";

import {
  Col,
  Form,
  Row
} from 'react-bootstrap';

import {itemsPerPageOptions, ResultsPage} from "../../utils/api";
import { TaskImpl, RunEnvironment } from "../../types/domain_types";
import styles from './TaskTable.module.scss';

import './style.scss';

interface Props {
  q: string;
  sortBy: string;
  descending: boolean;
  taskPage: ResultsPage<TaskImpl>;
  currentPage: number;
  rowsPerPage: number;
  shouldShowConfigModal: boolean;
  task: TaskImpl | null;
  editTask: (uuid: string, data: any) => Promise<void>;
  handleQueryChanged: (event: React.ChangeEvent<HTMLInputElement>) => void;
  handleRunEnvironmentChanged: (event: React.ChangeEvent<HTMLInputElement>) => void;
  handleSortChanged: (ordering?: string, toggleDirection?: boolean) => Promise<void>;
  loadTasks: () => Promise<void>;
  handlePageChanged: (currentPage: number) => void;
  handleSelectItemsPerPage: (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => void;
  handleDeletion: (uuid: string) => Promise<void>;
  handleActionRequested: (action: string | undefined, cbData: any) => Promise<void>;
  taskUuidToInProgressOperation: any;
  runEnvironments: RunEnvironment[];
  selectedRunEnvironmentUuid: string;
}

const TaskTable = (props: Props) => (
  <Fragment>
    <div>
      <Form inline>
        <Form.Label>Run Environment:</Form.Label>
        <Form.Control
          as="select"
          onChange={props.handleRunEnvironmentChanged}
          value={props.selectedRunEnvironmentUuid}
          className={'ml-sm-3 ' + styles.runEnvironmentSelector}
          size="sm"
        >
          <option key="all" value="">Show all</option>
          {
            props.runEnvironments.map((runEnvironment: any) => {
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
    <div className="d-flex justify-content-between align-items-center">
      <div className={styles.searchContainer}>
        <Form.Control
          type="text"
          onChange={props.handleQueryChanged}
          onKeyDown={(keyEvent: any) => {
            if (keyEvent.key === 'Enter') {
              props.loadTasks();
            }
          }}
          placeholder="Search Tasks"
          value={props.q || ''}
        />
      </div>
      <TablePagination
        component="div"
        labelRowsPerPage="Showing "
        count={props.taskPage.count}
        rowsPerPage={props.rowsPerPage}
        page={props.currentPage}
        onPageChange={(event) => null}
      />
    </div>
    <Table striped bordered responsive hover size="sm">
      <TableHeader
        handleSort={props.handleSortChanged}
        descending={props.descending}
        sortBy={props.sortBy}
      />
      <TableBody
        tasks={props.taskPage.results}
        task={props.task}
        handleDeletion={props.handleDeletion}
        handleActionRequested={props.handleActionRequested}
        taskUuidToInProgressOperation={props.taskUuidToInProgressOperation}
        editTask={props.editTask}
      />
    </Table>
    <DefaultPagination
      currentPage={props.currentPage}
      pageSize={props.rowsPerPage}
      count={props.taskPage.count}
      handleClick={props.handlePageChanged}
      handleSelectItemsPerPage={props.handleSelectItemsPerPage}
      itemsPerPageOptions={itemsPerPageOptions}
    />
  </Fragment>
);

export default TaskTable;
