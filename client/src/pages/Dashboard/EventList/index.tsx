import { AxiosError, isCancel } from 'axios';

import {
  AnyEvent, RunEnvironment
} from '../../../types/domain_types';

import {
  makeEmptyResultsPage,
  fetchRunEnvironments,
  fetchEvents
} from '../../../utils/api';

import React, { Fragment, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { GlobalContext } from '../../../context/GlobalContext';

import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import { transformSearchParams, updateSearchParams } from '../../../utils/url_search';

import Loading from '../../../components/Loading';
import EventTable from '../../../components/EventList/EventTable';
import styles from './index.module.scss';

const EventList = (props: AbortSignalProps) => {
  const {
    abortSignal
  } = props;

  const { currentGroup } = useContext(GlobalContext);

  const [areRunEnvironmentsLoading, setAreRunEnvironmentsLoading] = useState(false);
  const [runEnvironments, setRunEnvironments] = useState<Array<RunEnvironment>>([]);
  const [areEventsLoading, setAreEventsLoading] = useState(true);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [eventPage, setEventPage] = useState(
    makeEmptyResultsPage<AnyEvent>());

  const [loadEventsAbortController, setLoadEventsAbortController] = useState<AbortController | null>(null);
  const [eventTimeDescending, setEventTimeDescending] = useState(true);

  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    document.title = 'CloudReactor - Events';
  }, []);

  const mounted = useRef(false);

  const loadRunEnvironments = useCallback(async () => {
    setAreRunEnvironmentsLoading(true);
    try {
      const page = await fetchRunEnvironments({
        groupId: currentGroup?.id,
        abortSignal
      });

      setRunEnvironments(page.results);
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request canceled: ' + error.message);
      }
    } finally {
      setAreRunEnvironmentsLoading(false);
    }
  }, []);

  const loadEvents = useCallback(async (
    ordering?: string,
    toggleDirection?: boolean
  ) => {
    const {
      q,
      sortBy,
      descending,
      selectedRunEnvironmentUuids,
      rowsPerPage,
      currentPage
    } = transformSearchParams(searchParams, false);

    const minSeverity = searchParams.get('min_severity') || undefined;
    const maxSeverity = searchParams.get('max_severity') || undefined;
    const eventTypesParam = searchParams.get('event_type') ?? undefined;
    const eventTypes = eventTypesParam ? eventTypesParam.split(',').filter(Boolean) : undefined;
    const acknowledgedStatus = searchParams.get('acknowledged_status') || undefined;
    const resolvedStatus = searchParams.get('resolved_status') || undefined;

    if (loadEventsAbortController) {
      loadEventsAbortController.abort('Operation superceded');
    }
    const updatedLoadEventsAbortController = new AbortController();
    setLoadEventsAbortController(updatedLoadEventsAbortController);

    let finalOrdering = ordering ?? sortBy ?? 'event_at';
    let finalDescending = toggleDirection ? !descending : descending;

    if (ordering && (ordering === sortBy)) {
      finalDescending = toggleDirection ? !descending : descending;
    } else if (!ordering && !sortBy) {
      // Initial load without sort_by in URL. Default to event_at descending.
      finalDescending = true;
    }

    if (finalDescending) {
      finalOrdering = '-' + finalOrdering;
    }

    // Append event_at as secondary sort field, but only if it's not already the primary sort
    const sortFields = [finalOrdering];
    const primarySortField = finalOrdering.startsWith('-') ? finalOrdering.substring(1) : finalOrdering;
    if (primarySortField !== 'event_at') {
      sortFields.push(eventTimeDescending ? '-event_at' : 'event_at');
    }
    const finalSortBy = sortFields.join(',');

    setAreEventsLoading(true);

    try {
      const fetchedPage = await fetchEvents({
        groupId: currentGroup?.id,
        q: q ?? undefined,
        sortBy: finalSortBy,
        runEnvironmentUuids: selectedRunEnvironmentUuids,
        minSeverity,
        maxSeverity,
        eventTypes,
        acknowledgedStatus,
        resolvedStatus,
        offset: currentPage * rowsPerPage,
        maxResults: rowsPerPage,
        abortSignal: updatedLoadEventsAbortController.signal
      });

      setEventPage(fetchedPage);
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request canceled: ' + error.message);
        return;
      }

      const axiosError = error as AxiosError;
      console.error('Failed to load events', axiosError);
    } finally {
      setAreEventsLoading(false);
      setIsInitialLoad(false);
    }
  }, [location, eventTimeDescending]);

  const handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    updateSearchParams(searchParams, setSearchParams, rowsPerPage, 'rows_per_page');
  };

  const handleSortChanged = useCallback(async (ordering?: string, toggleDirection?: boolean) => {
    // When a new sortable column is selected, clear any previous multi-column sort
    // and reset to just that column + event_at (secondary)
    const currentSortBy = searchParams.get('sort_by');
    const currentDescending = searchParams.get('descending') === 'true';

    let nextDescending = false;
    if (ordering === currentSortBy) {
      nextDescending = toggleDirection ? !currentDescending : currentDescending;
    } else {
      // New column selected. Default to ascending for most columns,
      // but event_at uses the preserved direction.
      nextDescending = (ordering === 'event_at') ? eventTimeDescending : false;
    }

    if (ordering === 'event_at') {
      setEventTimeDescending(nextDescending);
    }

    const params = new URLSearchParams(searchParams);
    if (ordering) {
      params.set('sort_by', ordering);
    } else {
      params.delete('sort_by');
    }

    if (nextDescending) {
      params.set('descending', 'true');
    } else {
      params.delete('descending');
    }

    params.delete('page');

    setSearchParams(params, { replace: true });
  }, [searchParams, setSearchParams, eventTimeDescending]);

  const handleQueryChanged = useCallback((
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const q = event.target.value;
    updateSearchParams(searchParams, setSearchParams, q, 'events_q');
  }, [location]);

  const handlePageChanged = useCallback((currentPage: number) => {
    updateSearchParams(searchParams, setSearchParams, currentPage + 1, 'page');
  }, [location]);

  const handleSelectedRunEnvironmentUuidsChanged = useCallback((
    selectedRunEnvironmentUuids?: string[]
  ) => {
    updateSearchParams(searchParams, setSearchParams, selectedRunEnvironmentUuids,
      'run_environment__uuid');
  }, [location]);

  const handleMinSeverityChanged = useCallback((severity: string) => {
    updateSearchParams(searchParams, setSearchParams, severity || undefined, 'min_severity');
  }, [location]);

  const handleMaxSeverityChanged = useCallback((severity: string) => {
    updateSearchParams(searchParams, setSearchParams, severity || undefined, 'max_severity');
  }, [location]);

  const handleEventTypesChanged = useCallback((types?: string[]) => {
    updateSearchParams(searchParams, setSearchParams, types && types.length ? types : undefined, 'event_type');
  }, [location]);

  const handleAcknowledgedStatusChanged = useCallback((status: string) => {
    updateSearchParams(searchParams, setSearchParams, status || undefined, 'acknowledged_status');
  }, [location]);

  const handleResolvedStatusChanged = useCallback((status: string) => {
    updateSearchParams(searchParams, setSearchParams, status || undefined, 'resolved_status');
  }, [location]);

  const cleanupLoading = () => {
    if (loadEventsAbortController) {
      loadEventsAbortController.abort('Operation canceled after component unmounted');
    }
  };

  useEffect(() => {
    mounted.current = true;

    loadRunEnvironments()

    return () => {
      mounted.current = false;
      cleanupLoading();
    };
  }, []);

  useEffect(() => {
    loadEvents();

    return () => {
      cleanupLoading();
    };
  }, [location]);

  const {
    q,
    sortBy,
    descending,
    selectedRunEnvironmentUuids,
    rowsPerPage,
    currentPage
  } = transformSearchParams(searchParams, false);

  const minSeverity = searchParams.get('min_severity') || undefined;
  const maxSeverity = searchParams.get('max_severity') || undefined;
  const acknowledgedStatus = searchParams.get('acknowledged_status') || undefined;
  const resolvedStatus = searchParams.get('resolved_status') || undefined;

  const finalSortBy = (sortBy ?? 'event_at');
  const finalDescending = descending ?? true;

  const eventTableProps = {
    handleSelectedRunEnvironmentUuidsChanged,
    handleQueryChanged,
    handleMinSeverityChanged,
    handleMaxSeverityChanged,
    eventTypes: (searchParams.get('event_type') ?? undefined) ? (searchParams.get('event_type') || '').split(',').filter(Boolean) : undefined,
    handleEventTypesChanged,
    handleAcknowledgedStatusChanged,
    handleResolvedStatusChanged,
    loadEvents,
    handleSortChanged,
    handlePageChanged,
    handleSelectItemsPerPage,
    q,
    minSeverity,
    maxSeverity,
    acknowledgedStatus,
    resolvedStatus,
    sortBy: finalSortBy,
    descending: finalDescending,
    currentPage,
    rowsPerPage,
    eventPage,
    runEnvironments,
    selectedRunEnvironmentUuids,
    onEventAcknowledged: () => loadEvents(),
  };

  return (
    <Fragment>
      {
        (isInitialLoad && (areRunEnvironmentsLoading || areEventsLoading)) ? (
          <Loading />
        ) : (
          <div className={styles.container}>
            <BreadcrumbBar
              firstLevel="Events"
            />

            <EventTable {...eventTableProps} />
          </div>
        )
      }
    </Fragment>
  );
};

export default abortableHoc(EventList);
