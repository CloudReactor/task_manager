import * as C from './constants';
import * as api from './api';
import {TaskExecution, Task} from '../types/domain_types';

import React from 'react';
import { Link } from 'react-router-dom';

import { createModal } from 'react-modal-promise';

import swal from 'sweetalert';

import StartTaskModal from '../components/StartTaskModal/StartTaskModal';

const moment = require('moment');
require('moment-duration-format');

export const displayStatus = (
  status: string,
  isService: boolean,
  forExecutionDetail: boolean = false
): string => {

  if (status === C.TASK_EXECUTION_STATUS_MANUALLY_STARTED) {
    return 'Starting';
  }

  if (isService) {
    switch (status) {
      case C.TASK_EXECUTION_STATUS_RUNNING:
        return 'Up';
      case C.TASK_EXECUTION_STATUS_SUCCEEDED:
        if (forExecutionDetail) {
          return 'EXITED';
        } else {
          return 'DOWN';
        }

      default:
        if (!forExecutionDetail) {
          return 'DOWN';
        }
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

export const colorPicker = (status: string, isService: boolean): string => {
  if (isService) {
    if (status === C.TASK_EXECUTION_STATUS_RUNNING) {
      return 'success';
    }
    return 'danger';
  } else {
    switch (status) {
      case C.TASK_EXECUTION_STATUS_RUNNING:
        return 'success';

      case C.TASK_EXECUTION_STATUS_SUCCEEDED:
        return 'success';

      case C.TASK_EXECUTION_STATUS_FAILED:
      case C.TASK_EXECUTION_STATUS_ABORTED:
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
  fallback: string = 'N/A', negative_value = 'Unlimited') : String {
  if (typeof x === 'number') {
    if (negative_value && (x < 0)) {
      return negative_value;
    }
    return moment.duration(x, 'seconds').format(
      'd [days], h [hours], m [minutes], s [seconds]', {
        trim: 'both mid'
      });
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

export function makeLink(value: string | null, url?: string | null): any {
  const v = value ?? 'N/A';
  if (!url) {
    return v;
  }

  return /^https?:\/\//.test(url) ? <a key={v} href={url}>{v}</a> :
    <Link key={value} to={url}>{v}</Link>;
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
  taskExecutionUuid: string, onConfirmation?: (confirmed: boolean) => void):
  Promise<TaskExecution | null> => {
  const changeStatus = await swal({
    title: `Are you sure you want to stop the Task '${task.name}'?`,
    buttons: ['no', 'yes'],
    icon: 'warning',
    dangerMode: true
  });

  if (onConfirmation) {
    onConfirmation(changeStatus);
  }

  if (changeStatus) {
    return api.stopTaskExecution(taskExecutionUuid);
  }

  return Promise.resolve(null);
};

export const startTaskExecution = async (task: Task, onConfirmation?: (confirmed: boolean) => void): Promise<TaskExecution | null> => {
  const modal = createModal(StartTaskModal);

  const taskExecutionProps = await modal({task});

  if (onConfirmation) {
    onConfirmation(!!taskExecutionProps);
  }

  if (taskExecutionProps) {
    return api.startTaskExecution(task.uuid, taskExecutionProps);
  }

  return Promise.resolve(null);
};