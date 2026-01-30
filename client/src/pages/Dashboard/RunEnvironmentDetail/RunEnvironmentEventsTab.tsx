import { AxiosError, isCancel } from 'axios';

import {
  Event, RunEnvironment
} from '../../../types/domain_types';

import {
  makeEmptyResultsPage,
  fetchEvents
} from '../../../utils/api';

import React, { Fragment, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import { GlobalContext } from '../../../context/GlobalContext';

import { transformSearchParams, updateSearchParams } from '../../../utils/url_search';

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
    makeEmptyResultsPage<Event>());

  const [loadEventsAbortController, setLoadEventsAbortController] = useState<AbortController | null>(null);

  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  const mounted = useRef(false);

  const loadEvents = useCallback(async (
    ordering?: string,
    toggleDirection?: boolean
  ) => {
    const {
      sortBy,
      descending,
      rowsPerPage,
      currentPage
    } = transformSearchParams(searchParams, true);

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
        runEnvironmentUuids: [runEnvironment.uuid],
        sortBy: finalOrdering,
        offset: currentPage * rowsPerPage,
        maxResults: rowsPerPage,
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
  }, [location, runEnvironment.uuid]);

  const handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    updateSearchParams(searchParams, setSearchParams, rowsPerPage, 'rows_per_page');
  };

  const handleSortChanged = useCallback(async (ordering?: string, toggleDirection?: boolean) => {
    updateSearchParams(searchParams, setSearchParams, ordering, 'sort_by');
  }, [location]);

  const handlePageChanged = useCallback((currentPage: number) => {
    updateSearchParams(searchParams, setSearchParams, currentPage + 1, 'page');
  }, [location]);

  const cleanupLoading = () => {
    if (loadEventsAbortController) {
      loadEventsAbortController.abort('Operation canceled after component unmounted');
    }
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
    sortBy,
    descending,
    rowsPerPage,
    currentPage
  } = transformSearchParams(searchParams, true);

  const finalSortBy = (sortBy ?? 'event_at');
  const finalDescending = descending ?? true;

  const eventTableProps = {
    loadEvents,
    handleSortChanged,
    handlePageChanged,
    handleSelectItemsPerPage,
    showFilters: false,
    showRunEnvironmentColumn: false,
    showTaskWorkflowColumn: true,
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

export default abortableHoc(RunEnvironmentEventsTab);
