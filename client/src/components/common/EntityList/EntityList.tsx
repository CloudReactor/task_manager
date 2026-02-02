import _ from 'lodash';

import {
  ACCESS_LEVEL_DEVELOPER,
  ACCESS_LEVEL_SUPPORT
} from '../../../utils/constants';

import { ResultsPage, makeEmptyResultsPage } from '../../../utils/api';

import React, { useContext, useEffect, useState, Fragment } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

import {
  Alert,
  Button,
  Row,
  Col,
  Pagination
} from 'react-bootstrap';

import * as UIC from '../../../utils/ui_constants';
import makeAbortable from '../../../utils/abortable_hook';

import {
  accessLevelForCurrentGroup,
  GlobalContext, GlobalContextType
} from '../../../context/GlobalContext';

import Loading from '../../Loading';
import BreadcrumbBar from '../../BreadcrumbBar/BreadcrumbBar';

import styles from './index.module.scss';

type Props = Record<string, never>;

export type ListRenderProps<T> = {
  handleSelection: (string) => void;
  page: ResultsPage<T>;
}

export type FetchPageProps = {
  groupId?: number;
  offset: number;
  maxResults?: number;
  abortSignal: AbortSignal;
  context: GlobalContextType;
}

export type EntityListProps<T> = {
  entityName: string;
  pluralEntityName?: string;
  minAccessLevelToCreate?: number;
  minAccessLevelToViewDetails?: number;
  fetchPage: (p: FetchPageProps) => Promise<ResultsPage<T>>;
  renderEntities: (p: ListRenderProps<T>) => any;
}

export function makeEntityList<T>({
  entityName,
  pluralEntityName,
  minAccessLevelToCreate,
  minAccessLevelToViewDetails,
  fetchPage,
  renderEntities
}: EntityListProps<T>) {
  pluralEntityName = pluralEntityName ?? (entityName + 's');
  minAccessLevelToCreate = minAccessLevelToCreate ?? ACCESS_LEVEL_DEVELOPER
  minAccessLevelToViewDetails = minAccessLevelToViewDetails ?? ACCESS_LEVEL_SUPPORT

  const EntityList = (props: Props) => {
    const location = useLocation();
    const params = new URLSearchParams(location.search);
    const pageSize = Number(params.get('max_results') ?? UIC.DEFAULT_PAGE_SIZE);
    const initialOffset = (Number(params.get('page') ?? 1) - 1) * UIC.DEFAULT_PAGE_SIZE;

    const context = useContext(GlobalContext);
    const accessLevel = accessLevelForCurrentGroup(context);

    if (!accessLevel) {
      return (
        <p>You don&apos;t have permission to access to this page.</p>
      );
    }

    const { currentGroup } = context;

    const [isLoading, setLoading] = useState(true);
    const [page, setPage] = useState(makeEmptyResultsPage<T>());
    const [loadErrorMessage, setLoadErrorMessage] = useState('');
    const [offset, setOffset] = useState(initialOffset);

    const lastPageOffset = page ?
      Math.max((Math.floor(page.count / pageSize) - 1) * pageSize, 0) : 0;

    useEffect(() => {
      document.title = `CloudReactor - ${pluralEntityName}`;
    }, []);

    const navigate = useNavigate();

    makeAbortable(async (abortSignal) => {
      try {
        const page = await fetchPage({
          groupId: currentGroup?.id,
          offset,
          maxResults: pageSize,
          abortSignal,
          context
        });
        setPage(page);
      } catch (ex) {
        console.error(ex);
        setLoadErrorMessage(`An error occurred loading ${pluralEntityName}.`);
      } finally {
        setLoading(false);
      }
    }, [offset, currentGroup]);

    const handleSelection = (uuid: string) => {
      if (uuid === 'new') {
        if (!minAccessLevelToCreate || (accessLevel < minAccessLevelToCreate)) {
          return;
        }
      } else if (!minAccessLevelToViewDetails ||
          (accessLevel < minAccessLevelToViewDetails)) {
        return;
      }

      navigate(location.pathname + `/${uuid}`);
    }

    const setOffsetAndPageQuery = (i: number)  => {
      setOffset(i);

      let path = location.pathname;

      const params = new URLSearchParams();

      if (i > 0) {
        params.set('page', '' + (Math.floor(i / pageSize) + 1));
      }

      if (pageSize !== UIC.DEFAULT_PAGE_SIZE) {
        params.set('max_results', '' + pageSize);
      }

      if (Array.from(params.keys()).length > 0) {
        path += '?' + params.toString();
      }

      navigate(path, { replace: true });
    }

    const goToFirstPage = () => {
      setOffsetAndPageQuery(0);
    }

    const goToPreviousPage = () => {
      setOffsetAndPageQuery(Math.max(0, offset - pageSize));
    }

    const goToNextPage = () => {
      setOffsetAndPageQuery(offset + pageSize);
    }

    const goToLastPage = () => {
      if (page) {
        setOffsetAndPageQuery(lastPageOffset);
      }
    }

    return (
      <div className={styles.container}>
        <BreadcrumbBar
          firstLevel={pluralEntityName}
          secondLevel={null}
        />

        {
          accessLevel &&  minAccessLevelToCreate &&
          (accessLevel >= minAccessLevelToCreate) && (
            <div>
              <Button
                variant='outline-primary'
                onClick={() => handleSelection('new')}
              >
                <i className="fas fa-plus pl-2 pr-2"/>
                Add {entityName}
              </Button>
            </div>
          )
        }

        {
          loadErrorMessage &&
          <Alert variant="danger">
            { loadErrorMessage }
          </Alert>
        }

        <div style={{flexWrap: 'wrap'}}>
          {
            isLoading ? <Loading /> : ((page?.count ?? 0) === 0) ? (
              <p className="mt-3">
                There are no {pluralEntityName} created yet.
              </p>
            ) : (
              <Fragment>
                { renderEntities({ page, handleSelection }) }

                <Row className="mt-3">
                  <Col>
                    <Pagination size="lg">
                      <Pagination.First disabled={offset <= 0}
                      onClick={goToFirstPage} />

                      <Pagination.Prev disabled={offset <= 0}
                      onClick={goToPreviousPage} />

                      {
                        _.range(0, page.count, pageSize).map(i =>
                          <Pagination.Item key={i} active={i === offset}
                           onClick={() => setOffsetAndPageQuery(i)}>
                            { (i / pageSize) + 1 }
                          </Pagination.Item>
                        )
                      }

                      <Pagination.Next disabled={offset >= lastPageOffset}
                      onClick={goToNextPage} />
                      <Pagination.Last disabled={offset >= lastPageOffset}
                      onClick={goToLastPage} />
                    </Pagination>
                  </Col>
                </Row>
              </Fragment>
            )
          }
        </div>
      </div>
    );
  };

  return EntityList;
}
