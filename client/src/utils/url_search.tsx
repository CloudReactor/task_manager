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
    forExecutions: boolean = false,
    paramPrefix: string = ''): PageFetchOptions => {
  const descendingStr = searchParams.get(paramPrefix + 'descending');
  const sortBy = searchParams.get(paramPrefix + 'sort_by');

  const descending = descendingStr ? (descendingStr === 'true') :
    (sortBy ? false : undefined);

  let statusParamName = 'status';

  if (!forExecutions) {
    statusParamName = 'latest_' + (forWorkflows ? 'workflow' : 'task') + '_execution__' + statusParamName;
  }

  const selectedStatusesParamValue = searchParams.get(paramPrefix + statusParamName);

  let selectedStatuses: string[] | undefined;

  if (selectedStatusesParamValue) {
    selectedStatuses = selectedStatusesParamValue.split(',');
  }

  let selectedRunEnvironmentUuids: string[] | undefined;

  const selectedRunEnvironmentUuidsParamValue = searchParams.get(paramPrefix + 'run_environment__uuid');

  if (selectedRunEnvironmentUuidsParamValue) {
    selectedRunEnvironmentUuids = selectedRunEnvironmentUuidsParamValue.split(',');
  }

  return {
    q: searchParams.get(paramPrefix + 'q') ?? undefined,
    sortBy: searchParams.get(paramPrefix + 'sort_by') ?? undefined,
    descending,
    selectedRunEnvironmentUuids,
    selectedStatuses,
    rowsPerPage: Number(searchParams.get(paramPrefix + 'rows_per_page')) || UIC.DEFAULT_PAGE_SIZE,
    currentPage: Number(searchParams.get(paramPrefix + 'page') || 1) - 1
  };
}

export const updateSearchParams = (
  params: URLSearchParams,
  setSearchParams: (searchParams: URLSearchParams, options: any) => void,
  value: any,
  changeParam: string,
  prefix: string = ''
) => {
  const paramName = `${prefix}${changeParam}`;

  if (changeParam === 'sort_by') {
    const currentSortBy = params.get(paramName);
    if (value === currentSortBy) {
      // user is clicking on the column that's already sorted. So, toggle the sort order
      const descendingParamName = `${prefix}descending`;
      const isDescending = (params.get(descendingParamName) === 'true');

      if (isDescending) {
        params.delete(descendingParamName);
      } else {
        params.set(descendingParamName, 'true');
      }
    } else {
      params.set(paramName, value);
      params.delete(`${prefix}descending`);
    }
  } else if (changeParam === 'page') {
    if (value > 1) {
      params.set(paramName, value);
    } else {
      params.delete(paramName);
    }
  } else if (changeParam === 'descending') {
    if (value) {
      params.set(paramName, 'true')
    } else {
      params.delete(paramName);
    }
  } else {
    if (_.isArray(value)) {
      params.set(paramName, value.join(','));
    } else if (value) {
      params.set(paramName, value);
    } else {
      params.delete(paramName);
    }

    params.delete(`${prefix}descending`);
  }

  if ((changeParam !== 'page') || (value === 1)) {
    params.delete(`${prefix}page`);
  }

  setSearchParams(params, { replace: true });
}
