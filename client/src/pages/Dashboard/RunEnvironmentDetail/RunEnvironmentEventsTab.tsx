import { AxiosError, isCancel } from 'axios';

import {
  AnyEvent, RunEnvironment
} from '../../../types/domain_types';

import {
  makeEmptyResultsPage,
  fetchEvents
} from '../../../utils/api';

import React, { Fragment, useCallback, useContext, useEffect, useState, useMemo, ChangeEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { GlobalContext } from '../../../context/GlobalContext';

import Loading from '../../../components/Loading';
import EventTable from '../../../components/EventList/EventTable';

interface Props {
  runEnvironment: RunEnvironment;
}

type InnerProps = Props & AbortSignalProps;

const RunEnvironmentEventsTab = (props: InnerProps) => {
  const {
    runEnvironment,
    abortSignal
  } = props;

  const { currentGroup } = useContext(GlobalContext);

  const [areEventsLoading, setAreEventsLoading] = useState(true);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [eventPage, setEventPage] = useState(
    makeEmptyResultsPage<AnyEvent>());

  const [loadEventsAbortController, setLoadEventsAbortController] = useState<AbortController | null>(null);

  const [searchParams, setSearchParams] = useSearchParams();

  // Derive all filter state from URL parameters - memoized to prevent infinite loops
  const filterState = useMemo(() => {
    const rpp = searchParams.get('event_rows_per_page') ? parseInt(searchParams.get('event_rows_per_page')!) : 10;
    
    // Use 0-indexed pagination to match DefaultPagination component expectations
    const currentPage = 0;
    
    return {
      eventQuery: searchParams.get('event_q') ?? '',
      minSeverity: searchParams.get('event_min_severity') ?? '',
      maxSeverity: searchParams.get('event_max_severity') ?? '',
      eventTypes: searchParams.get('event_type') ? searchParams.get('event_type')!.split(',') : [],
      acknowledgedStatus: searchParams.get('event_acknowledged_status') ?? '',
      resolvedStatus: searchParams.get('event_resolved_status') ?? '',
      eventSortBy: searchParams.get('event_sort_by') ?? 'event_at',
      eventDescending: searchParams.get('event_descending') === 'true',
      currentPage,
      rowsPerPage: rpp
    };
  }, [searchParams]);

  const updateEventFiltersInUrl = useCallback((updates: Record<string, any>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0)) {
        newParams.delete(key);
      } else if (Array.isArray(value)) {
        newParams.set(key, value.join(','));
      } else {
        newParams.set(key, String(value));
      }
    });
    setSearchParams(newParams);
  }, [searchParams, setSearchParams]);

  const loadEvents = useCallback(async () => {
    if (loadEventsAbortController) {
      loadEventsAbortController.abort('Operation superceded');
    }
    const updatedLoadEventsAbortController = new AbortController();
    setLoadEventsAbortController(updatedLoadEventsAbortController);

    setAreEventsLoading(true);
    try {
      let sortBy = filterState.eventSortBy;
      if (filterState.eventDescending) {
        sortBy = '-' + sortBy;
      }
      const fetchedPage = await fetchEvents({
        groupId: currentGroup?.id,
        runEnvironmentUuids: [runEnvironment.uuid],
        q: filterState.eventQuery,
        sortBy: sortBy,
        minSeverity: filterState.minSeverity ? parseInt(filterState.minSeverity) : undefined,
        maxSeverity: filterState.maxSeverity ? parseInt(filterState.maxSeverity) : undefined,
        eventTypes: filterState.eventTypes.length > 0 ? filterState.eventTypes : undefined,
        acknowledgedStatus: filterState.acknowledgedStatus || undefined,
        resolvedStatus: filterState.resolvedStatus || undefined,
        offset: filterState.currentPage * filterState.rowsPerPage,
        maxResults: filterState.rowsPerPage,
        abortSignal
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
  }, [runEnvironment.uuid, currentGroup?.id, filterState, abortSignal]);

  const handleEventQueryChanged = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const newQuery = event.target.value;
    updateEventFiltersInUrl({ event_q: newQuery });
  }, [updateEventFiltersInUrl]);

  const handleMinSeverityChanged = useCallback((severity: string) => {
    updateEventFiltersInUrl({ event_min_severity: severity || undefined });
  }, [updateEventFiltersInUrl]);

  const handleMaxSeverityChanged = useCallback((severity: string) => {
    updateEventFiltersInUrl({ event_max_severity: severity || undefined });
  }, [updateEventFiltersInUrl]);

  const handleEventTypesChanged = useCallback((types?: string[]) => {
    updateEventFiltersInUrl({ event_type: types && types.length > 0 ? types : undefined });
  }, [updateEventFiltersInUrl]);

  const handleAcknowledgedStatusChanged = useCallback((status: string) => {
    updateEventFiltersInUrl({ event_acknowledged_status: status || undefined });
  }, [updateEventFiltersInUrl]);

  const handleResolvedStatusChanged = useCallback((status: string) => {
    updateEventFiltersInUrl({ event_resolved_status: status || undefined });
  }, [updateEventFiltersInUrl]);

  const handleSortChanged = useCallback(async (ordering?: string, toggleDirection?: boolean) => {
    if (!ordering) return;
    
    const currentSortBy = searchParams.get('event_sort_by') ?? 'event_at';
    const currentDescending = searchParams.get('event_descending') === 'true';
    
    if (ordering === currentSortBy && toggleDirection) {
      // Toggle direction if same field
      updateEventFiltersInUrl({ event_descending: !currentDescending });
    } else {
      // New field or not toggling
      updateEventFiltersInUrl({ event_sort_by: ordering, event_descending: true });
    }
  }, [searchParams, updateEventFiltersInUrl]);

  const handlePageChanged = useCallback((page: number) => {
    updateEventFiltersInUrl({ event_page: page });
  }, [updateEventFiltersInUrl]);

  const handleSelectItemsPerPage = useCallback((event: ChangeEvent<HTMLSelectElement>) => {
    const rpp = parseInt(event.target.value);
    updateEventFiltersInUrl({ event_rows_per_page: rpp, event_page: 1 });
  }, [updateEventFiltersInUrl]);

  const cleanupLoading = useCallback(() => {
    if (loadEventsAbortController) {
      loadEventsAbortController.abort('Operation canceled after component unmounted');
    }
  }, [loadEventsAbortController]);

  // Load events whenever loadEvents changes (which happens when filterState/URL changes)
  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanupLoading;
  }, [cleanupLoading]);

  return (
    <div>
      {
        isInitialLoad ? (
          <Loading />
        ) : (
          <Fragment>
            <EventTable
              eventPage={eventPage}
              q={filterState.eventQuery}
              handleQueryChanged={handleEventQueryChanged}
              minSeverity={filterState.minSeverity}
              maxSeverity={filterState.maxSeverity}
              handleMinSeverityChanged={handleMinSeverityChanged}
              handleMaxSeverityChanged={handleMaxSeverityChanged}
              eventTypes={filterState.eventTypes}
              handleEventTypesChanged={handleEventTypesChanged}
              acknowledgedStatus={filterState.acknowledgedStatus}
              handleAcknowledgedStatusChanged={handleAcknowledgedStatusChanged}
              resolvedStatus={filterState.resolvedStatus}
              handleResolvedStatusChanged={handleResolvedStatusChanged}
              sortBy={filterState.eventSortBy}
              descending={filterState.eventDescending}
              handleSortChanged={handleSortChanged}
              loadEvents={loadEvents}
              currentPage={filterState.currentPage}
              handlePageChanged={handlePageChanged}
              rowsPerPage={filterState.rowsPerPage}
              handleSelectItemsPerPage={handleSelectItemsPerPage}
              showFilters={true}
              showRunEnvironmentColumn={false}
              showTaskWorkflowColumn={true}
              showExecutionColumn={true}
            />
          </Fragment>
        )
      }
    </div>
  );
}

export default abortableHoc(RunEnvironmentEventsTab);
