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
  const isDescending = (params.get('descending') === 'true') || false;

  // TODO: remove empty values
  return Object.assign({}, {
    q: params.get('q') || '',
    sortBy: params.get('sort_by') || '',
    descending: isDescending,
    selectedRunEnvironmentUuid: params.get('selected_run_environment_uuid') || '',
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

  if (changeParam === 'sort_by' && value === params.get("sort_by")) {
    // user is clicking on the column that's already sorted. So, toggle the sort order
    const isDescending = params.get('descending') === 'true' ? 'false' : 'true';
    params.set('descending', isDescending);

  } else if ((changeParam === 'page') && (value === 1)) {
    params.delete('page');
  } else {
    // user is clicking on a different column than what's already sorted, or is entering a new search query.

    if ((value === null) || (value === undefined) || (value === '')) {
      params.delete(changeParam);
    } else {
      params.set(changeParam, value);
    }
  }

  const newQueryString = '?' + params.toString();
  history.replace({
    //pathname: location.pathname,
    search: newQueryString,
  })
}