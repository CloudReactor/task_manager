import { AxiosError, isCancel } from 'axios';

import {
  AnyEvent, Workflow
} from '../../../types/domain_types';

import {
  makeEmptyResultsPage,
  fetchEvents
} from '../../../utils/api';

import React, { Fragment, useCallback, useContext, useEffect, useRef, useState, ChangeEvent } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { GlobalContext } from '../../../context/GlobalContext';

import { transformSearchParams, updateSearchParams } from '../../../utils/url_search';

import Loading from '../../../components/Loading';
import EventTable from '../../../components/EventList/EventTable';

interface Props extends AbortSignalProps {
  workflow: Workflow;
}

const WorkflowEventsTab = (props: Props) => {
  const {
    workflow,
    abortSignal
  } = props;

  const { currentGroup } = useContext(GlobalContext);

  const [areEventsLoading, setAreEventsLoading] = useState(true);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [eventPage, setEventPage] = useState(
    makeEmptyResultsPage<AnyEvent>());

  const [loadEventsAbortController, setLoadEventsAbortController] = useState<AbortController | null>(null);

  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  const mounted = useRef(false);

  const loadEvents = useCallback(async (
    ordering?: string,
    toggleDirection?: boolean
  ) => {
    const {
      q,
      sortBy,
      descending,
      rowsPerPage,
      currentPage
    } = transformSearchParams(searchParams, true, 'event_');
    const minSeverity = searchParams.get('event_min_severity') ?? undefined;
    const maxSeverity = searchParams.get('event_max_severity') ?? undefined;
    const eventTypesParam = searchParams.get('event_type') ?? undefined;
    const eventTypes = eventTypesParam ? eventTypesParam.split(',').filter(Boolean) : undefined;
    const acknowledgedStatus = searchParams.get('event_acknowledged_status') ?? undefined;
    const resolvedStatus = searchParams.get('event_resolved_status') ?? undefined;

    if (loadEventsAbortController) {
      loadEventsAbortController.abort('Operation superceded');
    }
    const updatedLoadEventsAbortController = new AbortController();
    setLoadEventsAbortController(updatedLoadEventsAbortController);

    let finalOrdering = ordering ?? sortBy;
    let finalDescending = toggleDirection ? !descending : descending;

    if (ordering && (ordering === sortBy)) {
      finalDescending = toggleDirection ? !descending : descending;
    }

    if (finalDescending) {
      finalOrdering = '-' + finalOrdering;
    }

    setAreEventsLoading(true);

    try {
      const fetchedPage = await fetchEvents({
        groupId: currentGroup?.id,
        workflowUuid: workflow.uuid,
        q,
        sortBy: finalOrdering,
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
  }, [location, workflow.uuid]);

  const handleSelectItemsPerPage = (
    event: ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    updateSearchParams(searchParams, setSearchParams, rowsPerPage, 'event_rows_per_page');
  };

  const handleSortChanged = useCallback(async (ordering?: string, toggleDirection?: boolean) => {
    updateSearchParams(searchParams, setSearchParams, ordering, 'event_sort_by');
  }, [location]);

  const handlePageChanged = useCallback((currentPage: number) => {
    updateSearchParams(searchParams, setSearchParams, currentPage + 1, 'event_page');
  }, [location]);

  const handleQueryChanged = useCallback((
    event: ChangeEvent<HTMLInputElement>
  ) => {
    updateSearchParams(searchParams, setSearchParams, event.target.value, 'event_q');
  }, [location]);

  const cleanupLoading = () => {
    if (loadEventsAbortController) {
      loadEventsAbortController.abort('Operation canceled after component unmounted');
    }
  };

  const handleMinSeverityChanged = (severity: string) => {
    updateSearchParams(searchParams, setSearchParams, severity, 'event_min_severity');
  };

  const handleMaxSeverityChanged = (severity: string) => {
    updateSearchParams(searchParams, setSearchParams, severity, 'event_max_severity');
  };

  const handleEventTypesChanged = (types?: string[]) => {
    updateSearchParams(searchParams, setSearchParams, types && types.length ? types : undefined, 'event_type');
  };

  const handleAcknowledgedStatusChanged = (status: string) => {
    updateSearchParams(searchParams, setSearchParams, status, 'event_acknowledged_status');
  };

  const handleResolvedStatusChanged = (status: string) => {
    updateSearchParams(searchParams, setSearchParams, status, 'event_resolved_status');
  };

  useEffect(() => {
    mounted.current = true;

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
    rowsPerPage,
    currentPage
  } = transformSearchParams(searchParams, true, 'event_');

  const finalSortBy = (sortBy ?? 'event_at');
  const finalDescending = descending ?? true;

  const eventTableProps = {
    loadEvents,
    handleSortChanged,
    handlePageChanged,
    handleSelectItemsPerPage,
    handleQueryChanged,
    q,
    showFilters: true,
    minSeverity: searchParams.get('event_min_severity') ?? undefined,
    maxSeverity: searchParams.get('event_max_severity') ?? undefined,
    handleMinSeverityChanged,
    handleMaxSeverityChanged,
    eventTypes: (searchParams.get('event_type') ?? undefined) ? (searchParams.get('event_type') || '').split(',').filter(Boolean) : undefined,
    handleEventTypesChanged,
    acknowledgedStatus: searchParams.get('event_acknowledged_status') ?? undefined,
    resolvedStatus: searchParams.get('event_resolved_status') ?? undefined,
    handleAcknowledgedStatusChanged,
    handleResolvedStatusChanged,
    showRunEnvironmentColumn: false,
    showTaskWorkflowColumn: false,
    sortBy: finalSortBy,
    descending: finalDescending,
    currentPage,
    rowsPerPage,
    eventPage
  };

  return (
    <div>
      {
        isInitialLoad ? (
          <Loading />
        ) : (
          <Fragment>
            <EventTable {...eventTableProps} />
          </Fragment>
        )
      }
    </div>
  );
}

export default abortableHoc(WorkflowEventsTab);
