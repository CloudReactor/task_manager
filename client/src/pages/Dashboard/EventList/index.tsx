import { AxiosError, isCancel } from 'axios';

import {
  Event, RunEnvironment
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
    makeEmptyResultsPage<Event>());

  const [loadEventsAbortController, setLoadEventsAbortController] = useState<AbortController | null>(null);

  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

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
    } = transformSearchParams(searchParams, true);

    const minSeverity = searchParams.get('min_severity') || undefined;
    const maxSeverity = searchParams.get('max_severity') || undefined;

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
        q: q ?? undefined,
        sortBy: finalOrdering,
        runEnvironmentUuids: selectedRunEnvironmentUuids,
        minSeverity,
        maxSeverity,
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
  }, [location]);

  const handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const rowsPerPage = parseInt(event.target.value);
    updateSearchParams(searchParams, setSearchParams, rowsPerPage, 'rows_per_page');
  };

  const handleSortChanged = useCallback(async (ordering?: string, toggleDirection?: boolean) => {
    updateSearchParams(searchParams, setSearchParams, ordering, 'sort_by');
  }, [location]);

  const handleQueryChanged = useCallback((
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const q = event.target.value;
    updateSearchParams(searchParams, setSearchParams, q, 'q');
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
  } = transformSearchParams(searchParams, true);

  const minSeverity = searchParams.get('min_severity') || undefined;
  const maxSeverity = searchParams.get('max_severity') || undefined;

  const finalSortBy = (sortBy ?? 'event_at');
  const finalDescending = descending ?? true;

  const eventTableProps = {
    handleSelectedRunEnvironmentUuidsChanged,
    handleQueryChanged,
    handleMinSeverityChanged,
    handleMaxSeverityChanged,
    loadEvents,
    handleSortChanged,
    handlePageChanged,
    handleSelectItemsPerPage,
    q,
    minSeverity,
    maxSeverity,
    sortBy: finalSortBy,
    descending: finalDescending,
    currentPage,
    rowsPerPage,
    eventPage,
    runEnvironments,
    selectedRunEnvironmentUuids,
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
