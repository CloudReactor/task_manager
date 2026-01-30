import React, { Fragment } from 'react';

import { Event, RunEnvironment } from '../../types/domain_types';
import { ResultsPage } from '../../utils/api';

import "../../styles/tableStyles.scss";

import {
  Form,
  Table
} from 'react-bootstrap'

import { MenuItem, Select } from '@mui/material';

import RunEnvironmentSelector from "../common/RunEnvironmentSelector/RunEnvironmentSelector";
import EventTableHeader from "./EventTableHeader";
import EventTableBody from "./EventTableBody";
import styles from './EventTable.module.scss';

interface Props {
  q?: string;
  sortBy: string;
  descending: boolean;
  eventPage: ResultsPage<Event>;
  currentPage: number;
  rowsPerPage: number;
  runEnvironments?: RunEnvironment[];
  selectedRunEnvironmentUuids?: string[];
  showFilters?: boolean;
  showRunEnvironmentColumn?: boolean;
  showTaskWorkflowColumn?: boolean;
  minSeverity?: string;
  maxSeverity?: string;
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
