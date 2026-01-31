import React, { Fragment } from 'react';

import { AnyEvent, RunEnvironment } from '../../types/domain_types';
import { ResultsPage } from '../../utils/api';

import "../../styles/tableStyles.scss";

import {
  Form,
  Table
} from 'react-bootstrap'

import { MenuItem, Select, Checkbox, ListItemText } from '@mui/material';

import RunEnvironmentSelector from "../common/RunEnvironmentSelector/RunEnvironmentSelector";
import EventTableHeader from "./EventTableHeader";
import EventTableBody from "./EventTableBody";
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
  handleQueryChanged?: (event: React.ChangeEvent<HTMLInputElement>) => void;
  handleMinSeverityChanged?: (severity: string) => void;
  handleMaxSeverityChanged?: (severity: string) => void;
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
    { value: '', label: 'Any' },
    { value: 'CRITICAL', label: 'Critical', numericValue: 600 },
    { value: 'ERROR', label: 'Error', numericValue: 500 },
    { value: 'WARNING', label: 'Warning', numericValue: 400 },
    { value: 'INFO', label: 'Info', numericValue: 300 },
    { value: 'DEBUG', label: 'Debug', numericValue: 200 },
    { value: 'TRACE', label: 'Trace', numericValue: 100 },
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
              <Form.Group className="mr-3">
                <Form.Label className="mr-2" style={{ width: '135px', display: 'inline-block', textAlign: 'right' }}>Run Environment:</Form.Label>
                <div style={{ width: '250px', display: 'inline-block' }}>
                  <RunEnvironmentSelector
                    runEnvironments={runEnvironments}
                    selectedRunEnvironmentUuids={selectedRunEnvironmentUuids}
                    handleSelectedRunEnvironmentUuidsChanged={handleSelectedRunEnvironmentUuidsChanged} />
                </div>
              </Form.Group>
            )}
            {handleQueryChanged && (
              <Form.Group className="ml-auto">
                <Form.Control
                  type="search"
                  placeholder="Search"
                  value={q || ''}
                  onChange={handleQueryChanged}
                />
              </Form.Group>
            )}
          </Form>
          {(handleMinSeverityChanged || handleMaxSeverityChanged) && (
            <Form inline className="mb-2">
              {handleMinSeverityChanged && (
                <Form.Group className="mr-3">
                  <Form.Label className="mr-2" style={{ width: '135px', display: 'inline-block', textAlign: 'right' }}>Min Severity:</Form.Label>
                  <Select
                    value={minSeverity || ''}
                    onChange={(e) => handleMinSeverityChanged(e.target.value as string)}
                    style={{ width: '233px', minHeight: '38px' }}
                    displayEmpty
                  >
                    {severityOptions.map(opt => (
                      <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                    ))}
                  </Select>
                </Form.Group>
              )}
              {handleMaxSeverityChanged && (
                <Form.Group className="mr-3">
                  <Form.Label className="mr-2" style={{ width: '135px', display: 'inline-block', textAlign: 'right' }}>Max Severity:</Form.Label>
                  <Select
                    value={maxSeverity || ''}
                    onChange={(e) => handleMaxSeverityChanged(e.target.value as string)}
                    style={{ width: '233px', minHeight: '38px' }}
                    displayEmpty
                  >
                    {maxSeverityOptions.map(opt => (
                      <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                    ))}
                  </Select>
                </Form.Group>
              )}
              {handleEventTypesChanged && (
                <Form.Group className="mr-3 py-2">
                  <Form.Label className="mr-2" style={{ width: '135px', display: 'inline-block', textAlign: 'right' }}>Event Types:</Form.Label>
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
                    renderValue={(selected) => ((selected as string[])?.length ? (selected as string[]).join(', ') : 'Any')}
                    style={{ width: '233px', minHeight: '38px' }}
                    displayEmpty
                  >
                    {/* We don't have a canonical list of event types here; allow caller to control via initial props or use common types. */}
                    <MenuItem value=""><Checkbox checked={!(eventTypes && eventTypes.length > 0)} /><ListItemText primary="Any" /></MenuItem>
                    {/* Example/commonly used types - callers can still fetch by string values */}
                    <MenuItem value="insufficient_service_instances"><Checkbox checked={(eventTypes || []).indexOf('insufficient_service_instances') > -1} /><ListItemText primary="Insufficient Service Instances" /></MenuItem>
                    <MenuItem value="missing_heartbeat_detection"><Checkbox checked={(eventTypes || []).indexOf('missing_heartbeat_detection') > -1} /><ListItemText primary="Missing Heartbeat" /></MenuItem>
                    <MenuItem value="missing_scheduled_task_execution"><Checkbox checked={(eventTypes || []).indexOf('missing_scheduled_task_execution') > -1} /><ListItemText primary="Missing Scheduled Task Execution" /></MenuItem>
                    <MenuItem value="missing_scheduled_workflow_execution"><Checkbox checked={(eventTypes || []).indexOf('missing_scheduled_workflow_execution') > -1} /><ListItemText primary="Missing Scheduled Workflow Execution" /></MenuItem>
                    <MenuItem value="task_execution_status_change"><Checkbox checked={(eventTypes || []).indexOf('task_execution_status_change') > -1} /><ListItemText primary="Task Execution Status Change" /></MenuItem>
                    <MenuItem value="workflow_execution_status_change"><Checkbox checked={(eventTypes || []).indexOf('workflow_execution_status_change') > -1} /><ListItemText primary="Workflow Execution Status Change" /></MenuItem>
                  </Select>
                </Form.Group>
              )}
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
        />
      </Table>
    </Fragment>
  );
};

export default EventTable;
