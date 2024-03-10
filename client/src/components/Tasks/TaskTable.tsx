import { itemsPerPageOptions, ResultsPage } from "../../utils/api";
import { TaskImpl, RunEnvironment } from "../../types/domain_types";

import React, { Fragment } from "react";

import {
  Form,
  Table
} from 'react-bootstrap';

import { DebounceInput } from 'react-debounce-input';

import TablePagination from "@material-ui/core/TablePagination";
import StatusFilter from "../common/StatusFilter/StatusFilter";
import RunEnvironmentSelector from "../common/RunEnvironmentSelector/RunEnvironmentSelector";
import TableHeader from "./Table/TableHeader";
import TableBody from "./Table/TableBody";
import DefaultPagination from "../Pagination/Pagination";

import styles from './TaskTable.module.scss';

import './style.scss';

interface Props {
  q: string | undefined;
  sortBy: string;
  descending: boolean;
  taskPage: ResultsPage<TaskImpl>;
  currentPage: number;
  rowsPerPage: number;
  shouldShowConfigModal: boolean;
  task: TaskImpl | null;
  editTask: (uuid: string, data: any) => Promise<void>;
  handleQueryChanged: (event: React.ChangeEvent<HTMLInputElement>) => void;
  handleSelectedRunEnvironmentUuidsChanged: (uuids?: string[]) => void;
  handleSelectedStatusesChanged: (statuses?: string[]) => void;
  handleSortChanged: (ordering?: string, toggleDirection?: boolean) => Promise<void>;
  loadTasks: () => Promise<void>;
  handlePageChanged: (currentPage: number) => void;
  handleSelectItemsPerPage: (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => void;
  handleDeletion: (task: TaskImpl) => Promise<void>;
  handleActionRequested: (action: string | undefined, cbData: any) => Promise<void>;
  taskUuidToInProgressOperation: Record<string, string>;
  runEnvironments: RunEnvironment[];
  selectedRunEnvironmentUuids?: string[];
  selectedStatuses?: string[];
}

const TaskTable = (props: Props) => (
  <Fragment key="taskTable">
    <div>
      <Form inline>
        <Form.Group>
          <Form.Label className="mr-3">Run Environment:</Form.Label>
          <RunEnvironmentSelector
            runEnvironments={props.runEnvironments}
            selectedRunEnvironmentUuids={props.selectedRunEnvironmentUuids}
            handleSelectedRunEnvironmentUuidsChanged={props.handleSelectedRunEnvironmentUuidsChanged} />
        </Form.Group>
        <Form.Group>
          <Form.Label className="mr-3 mt-3 mb-3">Status:</Form.Label>
          <StatusFilter selectedStatuses={props.selectedStatuses}
           handleSelectedStatusesChanged={props.handleSelectedStatusesChanged} />
        </Form.Group>
      </Form>
    </div>
    <div className="d-flex justify-content-between align-items-center">
      <div className={styles.searchContainer}>
        <Form.Control type="search" as={DebounceInput}
          onChange={props.handleQueryChanged}
          onKeyDown={(keyEvent: any) => {
            if (keyEvent.key === 'Enter') {
              props.loadTasks();
            }
          }}
          placeholder="Search Tasks"
          value={props.q || ''}
          debounceTimeout={250}
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
