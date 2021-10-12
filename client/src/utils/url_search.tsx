import * as UIC from '../utils/ui_constants';

interface urlParams {
  q?: string;
  sortBy?: string;
  descending?: boolean;
  selectedRunEnvironmentUuid?: string;
  rowsPerPage?: number;
  currentPage?: number;
}

export const getParams = (location: any) => {
  const params = new URLSearchParams(location);
  const q = { q: params.get('q') || ''};
  const sortBy = { sortBy: params.get('sort_by') || '' };
  const isDescending = (params.get('descending') === 'true') || false;
  const descending = { descending: isDescending };
  const selectedRunEnvironmentUuid = { selectedRunEnvironmentUuid: params.get('selected_run_environment_uuid') || ''};
  const rowsPerPage = { rowsPerPage: Number(params.get('rows_per_page')) || UIC.DEFAULT_PAGE_SIZE };
  const currentPage = { currentPage: Number(params.get('page') || 1) - 1 }

  let queryParams: urlParams = { };
  Object.assign(queryParams, q);
  Object.assign(queryParams, sortBy);
  Object.assign(queryParams, descending);
  Object.assign(queryParams, selectedRunEnvironmentUuid);
  Object.assign(queryParams, rowsPerPage);
  Object.assign(queryParams, currentPage);
  return queryParams;
}

export const setURL = (
  location: any,
  history: any,
  value: any,
  changeParam: string,
) => {

  const params = new URLSearchParams(location.search);

  if (changeParam === 'sort_by' && value === params.get("sort_by")) {
    // user is clicking on the column that's already sorted. So, toggle the sort order
    const isDescending = params.get('descending') === 'true' ? 'false' : 'true';
    params.set('descending', isDescending);
  } else {
    // user is clicking on a different column than what's already sorted, or is entering a new search query.
    params.set(changeParam, value);
  }

  const newQueryString = '?' + params.toString();
  history.replace({
    pathname: location.pathname,
    search: newQueryString,
  })
}