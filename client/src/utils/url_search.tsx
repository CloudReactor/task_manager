import _ from 'lodash';

import * as UIC from '../utils/ui_constants';

interface urlParams {
  q?: string;
  sortBy?: string;
  descending?: boolean;
  selectedRunEnvironmentUuid?: string;
  rowsPerPage?: number;
  currentPage?: number;
}

export const getParams = (location: any, forWorkflows: boolean = false) => {
  const params = new URLSearchParams(location);
  const descendingStr = params.get('descending');
  const sortBy = params.get('sort_by');

  const descending = descendingStr ? (descendingStr === 'true') :
    (sortBy ? false : undefined);

  const selectedStatusesParamValue = params.get(
    forWorkflows ? 'latest_workflow_execution__status' :
    'latest_task_execution__status');

  let selectedStatuses: string[] | undefined;

  if (selectedStatusesParamValue) {
    selectedStatuses = selectedStatusesParamValue.split(',');
  }

  let selectedRunEnvironmentUuids: string[] | undefined;

  const selectedRunEnvironmentUuidsParamValue = params.get('run_environment_uuid');

  if (selectedRunEnvironmentUuidsParamValue) {
    selectedRunEnvironmentUuids = selectedRunEnvironmentUuidsParamValue.split(',');
  }

  return Object.assign({}, {
    q: params.get('q') ?? undefined,
    sortBy: params.get('sort_by') ?? undefined,
    descending,
    selectedRunEnvironmentUuids,
    selectedStatuses,
    rowsPerPage: Number(params.get('rows_per_page')) || UIC.DEFAULT_PAGE_SIZE,
    currentPage: Number(params.get('page') || 1) - 1
  });
}

export const setURL = (
  location: any,
  history: any,
  value: any,
  changeParam: string,
) => {
  const params = new URLSearchParams(location.search);

  if (changeParam === 'sort_by') {
    if (value === params.get('sort_by')) {
      // user is clicking on the column that's already sorted. So, toggle the sort order
      const isDescending = (params.get('descending') === 'true');

      if (isDescending) {
        params.delete('descending');
      } else {
        params.set('descending', 'true');
      }
    } else {
      params.set(changeParam, value);
      params.delete('descending');
    }
  } else if (changeParam === 'page') {
    if (value > 1) {
      params.set(changeParam, value);
    } else {
      params.delete('page');
    }
  } else if (changeParam === 'descending') {
    if (value) {
      params.set(changeParam, 'true')
    } else {
      params.delete(changeParam);
    }
  } else {
    if (_.isArray(value)) {
      params.set(changeParam, value.join(','));
    } else if (value) {
      params.set(changeParam, value);
    } else {
      params.delete(changeParam);
    }

    params.delete('descending');
  }

  if ((changeParam !== 'page') || (value === 1)) {
    params.delete('page');
  }

  const newQueryString = '?' + params.toString();
  history.replace({
    //pathname: location.pathname,
    search: newQueryString,
  })
}