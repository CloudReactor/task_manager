import React, { Fragment, ChangeEvent } from 'react';
import _ from 'lodash';

import { AnyEvent, RunEnvironment, EVENT_TYPE_DELAYED_TASK_EXECUTION_START, EVENT_TYPE_INSUFFICIENT_SERVICE_INSTANCES, EVENT_TYPE_MISSING_HEARTBEAT_DETECTION, EVENT_TYPE_MISSING_SCHEDULED_TASK_EXECUTION, EVENT_TYPE_MISSING_SCHEDULED_WORKFLOW_EXECUTION, EVENT_TYPE_TASK_EXECUTION_STATUS_CHANGE, EVENT_TYPE_WORKFLOW_EXECUTION_STATUS_CHANGE, EVENT_TYPES } from '../../types/domain_types';
import { ResultsPage, itemsPerPageOptions } from '../../utils/api';
import * as Constants from '../../utils/constants';

import "../../styles/tableStyles.scss";

import {
  Form,
  Table
} from 'react-bootstrap'

import { MenuItem, Select, Checkbox, ListItemText } from '@mui/material';

import RunEnvironmentSelector from "../common/RunEnvironmentSelector/RunEnvironmentSelector";
import EventTableHeader from "./EventTableHeader";
import EventTableBody from "./EventTableBody";
import DefaultPagination from "../Pagination/Pagination";
import styles from './EventTable.module.scss';

interface Props {
  q?: string;
  sortBy: string;
  descending: boolean;
  eventPage: ResultsPage<AnyEvent>;
  currentPage: number;
  rowsPerPage: number;
  runEnvironments?: RunEnvironment[];
  selectedRunEnvironmentUuids?: string[];
  showFilters?: boolean;
  showRunEnvironmentColumn?: boolean;
  showTaskWorkflowColumn?: boolean;
  minSeverity?: string;
  maxSeverity?: string;
  eventTypes?: string[];
  handleEventTypesChanged?: (types?: string[]) => void;
  handleSortChanged: (ordering?: string, toggleDirection?: boolean) => Promise<void>;
  handleSelectedRunEnvironmentUuidsChanged?: (uuids?: string[]) => void;
  handleQueryChanged?: (event: ChangeEvent<HTMLInputElement>) => void;
  handleMinSeverityChanged?: (severity: string) => void;
  handleMaxSeverityChanged?: (severity: string) => void;
  loadEvents: (
    ordering?: string,
    toggleDirection?: boolean
  ) => Promise<void>;
  handlePageChanged: (currentPage: number) => void;
  handleSelectItemsPerPage: (
    event: ChangeEvent<HTMLSelectElement>
  ) => void;
  onEventAcknowledged?: (eventUuid: string) => void;
}

const EventTable = (props: Props) => {
  const {
    q,
    showFilters = true,
    showRunEnvironmentColumn = true,
    showTaskWorkflowColumn = true,
    runEnvironments = [],
    selectedRunEnvironmentUuids,
    handleSelectedRunEnvironmentUuidsChanged,
    handleQueryChanged,
    minSeverity,
    maxSeverity,
    handleMinSeverityChanged,
    handleMaxSeverityChanged
    ,
    eventTypes,
    handleEventTypesChanged
  } = props;

  const severityOptions = [
    { value: '', label: 'Any', numericValue: undefined },
    ...Constants.NOTIFICATION_EVENT_SEVERITIES.map(numericValue => ({
      value: String(numericValue),
      label: _.startCase(Constants.NOTIFICATION_EVENT_SEVERITY_TO_LABEL[numericValue]),
      numericValue
    })).reverse() // Reverse to show highest severity first
  ];

  // Filter max severity options based on selected min severity
  const maxSeverityOptions = minSeverity && minSeverity !== ''
    ? (() => {
        const minOption = severityOptions.find(opt => opt.value === minSeverity);
        if (minOption && minOption.numericValue !== undefined) {
          return [
            { value: '', label: 'Any' },
            ...severityOptions.filter(opt =>
              opt.numericValue !== undefined && opt.numericValue >= minOption.numericValue
            )
          ];
        }
        return severityOptions;
      })()
    : severityOptions;

  return (
    <Fragment>
      {showFilters && (
        <div>
          <Form inline className="mb-2">
            {runEnvironments.length > 0 && handleSelectedRunEnvironmentUuidsChanged && (
              <Form.Group className="mr-3 mb-2">
                <Form.Label className={`mr-2 ${styles.filterLabel}`}>Run Environment:</Form.Label>
                <div className={styles.filterInput}>
                  <RunEnvironmentSelector
                    runEnvironments={runEnvironments}
                    selectedRunEnvironmentUuids={selectedRunEnvironmentUuids}
                    handleSelectedRunEnvironmentUuidsChanged={handleSelectedRunEnvironmentUuidsChanged} />
                </div>
              </Form.Group>
            )}
            {handleEventTypesChanged && (
              <Form.Group className="mr-3 mb-2 py-2">
                <Form.Label className={`mr-2 ${styles.filterLabel}`}>Event Types:</Form.Label>
                <div className={styles.filterInput}>
                  <Select
                    multiple
                    value={eventTypes || []}
                    onChange={(e) => {
                      const val = e.target.value as unknown;
                      const arr = Array.isArray(val) ? (val as string[]) : (String(val).split(','));
                      // If the special "Any" option (empty string) is selected,
                      // treat it as clearing the selection.
                      if (arr.indexOf('') > -1) {
                        handleEventTypesChanged?.(undefined);
                      } else {
                        handleEventTypesChanged?.(arr.length ? arr : undefined);
                      }
                    }}
                    renderValue={(selected) => ((selected as string[])?.length ? (selected as string[]).map(_.startCase).join(', ') : 'Any')}
                    style={{ minHeight: '38px' }}
                    displayEmpty
                  >                    
                    <MenuItem value=""><Checkbox checked={!(eventTypes && eventTypes.length > 0)} /><ListItemText primary="Any" /></MenuItem>                    
                    {EVENT_TYPES.map(eventType => (
                      <MenuItem key={eventType} value={eventType}>
                        <Checkbox checked={(eventTypes || []).indexOf(eventType) > -1} />
                        <ListItemText primary={_.startCase(eventType)} />
                      </MenuItem>
                    ))}
                  </Select>
                </div>
              </Form.Group>
            )}
          </Form>
          {(handleMinSeverityChanged || handleMaxSeverityChanged) && (
            <Form inline className="mb-2">
              {handleMinSeverityChanged && (
                <Form.Group className="mr-3 mb-3">
                  <Form.Label className={`mr-2 ${styles.filterLabel}`}>Min Severity:</Form.Label>
                  <div className={styles.filterInput}>
                    <Select
                      value={minSeverity || ''}
                      onChange={(e) => handleMinSeverityChanged(e.target.value as string)}
                      style={{ minHeight: '38px' }}
                      displayEmpty
                    >
                      {severityOptions.map(opt => (
                        <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                      ))}
                    </Select>
                  </div>
                </Form.Group>
              )}
              {handleMaxSeverityChanged && (
                <Form.Group className="mr-3 mb-3">
                  <Form.Label className={`mr-2 ${styles.filterLabel}`}>Max Severity:</Form.Label>
                  <div className={styles.filterInput}>
                    <Select
                      value={maxSeverity || ''}
                      onChange={(e) => handleMaxSeverityChanged(e.target.value as string)}
                      style={{ minHeight: '38px' }}
                      displayEmpty
                    >
                      {maxSeverityOptions.map(opt => (
                        <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                      ))}
                    </Select>
                  </div>
                </Form.Group>
              )}
            </Form>
          )}
          {handleQueryChanged && (
            <Form inline className="mb-2">
              <Form.Group className="mr-3">
                <Form.Label className={`mr-2 ${styles.filterLabel}`}>Search:</Form.Label>
                <div className={styles.searchInput}>
                  <Form.Control
                    type="search"
                    placeholder="Search"
                    value={q || ''}
                    onChange={handleQueryChanged}
                    style={{ width: '100%' }}
                  />
                </div>
              </Form.Group>
            </Form>
          )}
        </div>
      )}

      <Table striped bordered hover className={styles.table}>
        <EventTableHeader
          sortBy={props.sortBy}
          descending={props.descending}
          onSortChanged={props.handleSortChanged}
          showRunEnvironmentColumn={showRunEnvironmentColumn}
          showTaskWorkflowColumn={showTaskWorkflowColumn}
        />
        <EventTableBody
          eventPage={props.eventPage}
          currentPage={props.currentPage}
          rowsPerPage={props.rowsPerPage}
          handlePageChanged={props.handlePageChanged}
          handleSelectItemsPerPage={props.handleSelectItemsPerPage}
          showRunEnvironmentColumn={showRunEnvironmentColumn}
          showTaskWorkflowColumn={showTaskWorkflowColumn}
          onEventAcknowledged={props.onEventAcknowledged}
        />
      </Table>

      <div className="mt-3">
        <DefaultPagination
          currentPage={props.currentPage}
          pageSize={props.rowsPerPage}
          count={props.eventPage.count}
          handleClick={props.handlePageChanged}
          handleSelectItemsPerPage={props.handleSelectItemsPerPage}
          itemsPerPageOptions={itemsPerPageOptions}
        />
      </div>
    </Fragment>
  );
};

export default EventTable;
