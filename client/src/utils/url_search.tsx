import _ from 'lodash';

import * as UIC from '../utils/ui_constants';

interface PageFetchOptions {
  q?: string;
  sortBy?: string;
  descending?: boolean;
  selectedStatuses?: string[];
  selectedRunEnvironmentUuids?: string[];
  rowsPerPage: number;
  currentPage: number;
}

export const transformSearchParams = (searchParams: URLSearchParams,
    forWorkflows: boolean = false,
    forExecutions: boolean = false): PageFetchOptions => {
  const descendingStr = searchParams.get('descending');
  const sortBy = searchParams.get('sort_by');

  const descending = descendingStr ? (descendingStr === 'true') :
    (sortBy ? false : undefined);

  let statusParamName = 'status';

  if (!forExecutions) {
    statusParamName = 'latest_' + (forWorkflows ? 'workflow' : 'task') + '_execution__' + statusParamName;
  }

  const selectedStatusesParamValue = searchParams.get(statusParamName);

  let selectedStatuses: string[] | undefined;

  if (selectedStatusesParamValue) {
    selectedStatuses = selectedStatusesParamValue.split(',');
  }

  console.log(`statusParamName: ${statusParamName}, selectedStatuses: ${selectedStatuses}`);

  let selectedRunEnvironmentUuids: string[] | undefined;

  const selectedRunEnvironmentUuidsParamValue = searchParams.get('run_environment__uuid');

  if (selectedRunEnvironmentUuidsParamValue) {
    selectedRunEnvironmentUuids = selectedRunEnvironmentUuidsParamValue.split(',');
  }

  return {
    q: searchParams.get('q') ?? undefined,
    sortBy: searchParams.get('sort_by') ?? undefined,
    descending,
    selectedRunEnvironmentUuids,
    selectedStatuses,
    rowsPerPage: Number(searchParams.get('rows_per_page')) || UIC.DEFAULT_PAGE_SIZE,
    currentPage: Number(searchParams.get('page') || 1) - 1
  };
}

export const updateSearchParams = (
  params: URLSearchParams,
  setSearchParams: (searchParams: URLSearchParams, options: any) => void,
  value: any,
  changeParam: string,
) => {
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

  setSearchParams(params, { replace: true });
}
