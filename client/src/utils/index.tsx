import _ from 'lodash';
import moment from 'moment';

import React from 'react';
import { Link } from 'react-router-dom';
import { create } from 'react-modal-promise';

import * as C from './constants';
import * as api from './api';
import {TaskExecution, Task} from '../types/domain_types';

import AsyncConfirmationModal from '../components/common/AsyncConfirmationModal';
import StartTaskModal from '../components/StartTaskModal/StartTaskModal';

export const displayStatus = (
  enabled: boolean,
  status: string,
  isService: boolean,
  forExecutionDetail = false
): string => {

  if (status === C.TASK_EXECUTION_STATUS_MANUALLY_STARTED) {
    return 'Starting';
  }

  let statusLabel = '';
  if (isService) {
    switch (status) {
      case C.TASK_EXECUTION_STATUS_RUNNING:
        statusLabel = 'Up';
        break;
      case C.TASK_EXECUTION_STATUS_SUCCEEDED:
        if (forExecutionDetail) {
          statusLabel = 'EXITED';
        } else {
          statusLabel = 'DOWN';
        }
        break;

      default:
        if (!forExecutionDetail) {
          statusLabel = 'DOWN';
        }
    }
    if (enabled) {
      return statusLabel;
    } else {
      return _.startCase(statusLabel.toLowerCase());
    }
  }

  switch (status) {
    case C.TASK_EXECUTION_STATUS_SUCCEEDED:
    return 'Succeeded';

    case C.TASK_EXECUTION_STATUS_TERMINATED_AFTER_TIME_OUT:
    return 'TIMED OUT';
  }

  return status;
};

export const colorPicker = (status: string, isService: boolean, enabled: boolean=true): string => {
  if (isService) {
    if (enabled) {
      switch (status) {
        case C.TASK_EXECUTION_STATUS_RUNNING:
          return 'success';

        case C.TASK_EXECUTION_STATUS_ABORTED:
          return '';

        default:
          return 'danger';
      }
    } else {
      return '';
    }
  } else {
    switch (status) {
      case C.TASK_EXECUTION_STATUS_RUNNING:
      case C.TASK_EXECUTION_STATUS_SUCCEEDED:
        return 'success';

      case C.TASK_EXECUTION_STATUS_FAILED:
      case C.TASK_EXECUTION_STATUS_TERMINATED_AFTER_TIME_OUT:
        return 'danger';

      case C.TASK_EXECUTION_STATUS_ABANDONED:
        return 'warning';

      default:
        return '';
    }
  }
};


export function formatBoolean(x: boolean | null,
    fallback: string = 'N/A') : string {
  if (x === true) {
    return 'Yes'
  } else if (x === false) {
    return 'No'
  } else {
    return fallback;
  }
}

const DEFAULT_NUMBER_FORMATTER = new Intl.NumberFormat();

export function formatNumber(x: number | null,
    numberFormatter?: Intl.NumberFormat, fallback: string = 'N/A',
    negative_value: string = 'Unlimited') : string {
  if (typeof x === 'number') {
    if (negative_value && (x < 0)) {
      return negative_value;
    }
    return (numberFormatter ?? DEFAULT_NUMBER_FORMATTER).format(x);
  }
  return fallback;
}

export const dateTime = (time: number): string =>
  moment().diff(moment(time), 'minutes', true).toFixed(1);

export const timeFormat = (started_at: Date | null, incl_year?: boolean): string => {
  if (!started_at) {
    return 'N/A';
  }

  incl_year = incl_year ?? false;
  const format_string = (incl_year ? 'Y-' : '') + 'MM-DD HH:mm';
  return moment.utc(started_at).format(format_string);
}

export const timeDuration = (start: Date | null, end: Date | null) => {
  if (!start) {
    return 'Never started';
  }

  const endMoment = end ? moment(end) : moment();
  const date: string = moment
    .duration(endMoment.diff(moment(start)))
    .humanize();

  return date;
};

export function formatDuration(x: number | null,
  fallback: string = 'N/A', negative_value = 'Unlimited') : string {
  if (typeof x === 'number') {
    if (negative_value && (x < 0)) {
      return negative_value;
    }
    return moment.duration(x, 'seconds').humanize();
  }
  return fallback;
}

export const stringToNullOrInt = (s: string): number | null => {
  const x = ('' + s).trim();
  if (x === '') {
    return null;
  }

  return parseInt(x);
}

export const catchableToString = (ex: any): string => {
  return (ex instanceof Error) ? ex.message :
    ((typeof ex === 'string') ? ex : 'Unknown error');
}

export function makeLink(value?: string | null, url?: string | null, forceExternal?: boolean): any {
  if (!value) {
    return 'N/A';
  }

  if (!url) {
    return value;
  }

  return (forceExternal || /^https?:\/\//.test(url)) ? <a key={value} href={url}>{value}</a> :
    <Link key={value} to={url}>{value}</Link>;
}

export function makeLinks(labels: string[] | null, urls?: (string | null)[] | null | undefined) : any {
  if (labels === null) {
    return 'N/A'
  }

  if (labels.length === 0) {
    return 'None';
  }

  const elems: any[] = [];

  for (let i = 0; i < labels.length; i++) {
    elems.push(makeLink(labels[i], urls ? urls[i] : null));
    elems.push(', ');
  }

  elems.pop();

  return elems;
}

export const stopTaskExecution = async (task: Task,
  taskExecutionUuid: string,
  onConfirmation?: (confirmed: boolean) => void,
  abortSignal?: AbortSignal):
  Promise<TaskExecution | null> => {
  const modal = create(AsyncConfirmationModal);

  const changeStatus = await modal({
    title: 'Confirm Stop',
    confirmLabel: 'Stop',
    faIconName: 'stop',
    children: (
      <p>
        Are you sure you want to stop the execution of Task &lsquo;{task.name}&rsquo;?
      </p>
    )
  });

  if (onConfirmation) {
    onConfirmation(changeStatus);
  }

  if (changeStatus) {
    return api.stopTaskExecution(taskExecutionUuid, abortSignal);
  }

  return null;
};

export const startTaskExecution = async (task: Task,
    onConfirmation?: (confirmed: boolean) => void,
    abortSignal?: AbortSignal): Promise<TaskExecution | null> => {
  const modal = create(StartTaskModal);

  const taskExecutionProps = await modal({task});

  if (onConfirmation) {
    onConfirmation(!!taskExecutionProps);
  }

  if (taskExecutionProps) {
    return api.startTaskExecution(task.uuid, taskExecutionProps,
      abortSignal);
  }

  return null;
};
