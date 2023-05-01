import _ from 'lodash';
import { isCancel } from 'axios';

import * as C from '../../../utils/constants';

import { ApiKey } from '../../../types/domain_types';

import {
  deleteApiKey,
  fetchApiKeys,
  makeEmptyResultsPage
} from "../../../utils/api";

import React, { useContext, useEffect, useState } from "react";

import { useHistory, useLocation } from 'react-router-dom';

import { Alert, Form, Row, Col } from 'react-bootstrap';

import { createModal } from 'react-modal-promise';

import { DebounceInput } from 'react-debounce-input';

import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import AsyncConfirmationModal from '../../../components/common/AsyncConfirmationModal';

import { BootstrapVariant } from '../../../types/ui_types';
import * as UIC from '../../../utils/ui_constants';

import AccessDenied from '../../../components/AccessDenied';
import Loading from '../../../components/Loading';
import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import CustomButton from '../../../components/common/Button/CustomButton';
import ApiKeyTable from "../../../components/ApiKeyList/ApiKeyTable";
import { getParams, setURL } from '../../../utils/url_search';

import classNames from 'classnames';
import styles from './index.module.scss'


type Props = AbortSignalProps;

const ApiKeyList = ({
  abortSignal
}: Props) => {
  const context = useContext(GlobalContext);
  const {
    currentGroup
  } = context;

  const history = useHistory();
  const location = useLocation();

  const [flashBody, setFlashBody] = useState<string | null>(null);
  const [flashAlertVariant, setFlashAlertVariant] = useState<BootstrapVariant>('info');
  const [isLoading, setLoading] = useState(true);
  const [page, setPage] = useState(makeEmptyResultsPage<ApiKey>());

  const loadApiKeys = async () => {
    const {
      q,
      rowsPerPage,
      currentPage
    } = getParams(history.location.search);

    // user can't sort API keys, so just set here
    const sortBy = 'key';
    const descending = false;

    console.log(`loadApiKeys, q = ${q}`);

    setLoading(true);

    try {
      const fetchedPage = await fetchApiKeys({
        groupId: currentGroup?.id,
        q: q ?? undefined,
        sortBy,
        descending,
        offset: currentPage * rowsPerPage,
        maxResults: rowsPerPage,
        abortSignal
      });

      setPage(fetchedPage);
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request canceled: ' + error.message);
        return;
      }
    } finally {
      setLoading(false);
    }

    console.log('done loadApiKeys');
  };

  const handleQueryChanged = (
    event: React.ChangeEvent<HTMLInputElement>
  ): void => {
    setURL(history.location, history, 1, 'page');
    setURL(history.location, history, event.target.value, 'q');

    loadApiKeys();
  };

  const handlePageChanged = (currentPage: number) => {
    setURL(history.location, history, currentPage + 1, 'page');
    loadApiKeys();
  };

  /*const handlePrev = (): void =>
    this.setState({
      currentPage: Math.max(this.state.currentPage - 1, 0)
    }, this.loadApiKeys);

  const handleNext = (): void =>
    this.setState({
      currentPage: this.state.currentPage + 1
    }, this.loadApiKeys); */

  useEffect(() => {
    loadApiKeys();
  }, []);

  const accessLevel = accessLevelForCurrentGroup(context);

  if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
    return <AccessDenied />;
  }

  const handleDeletionRequest = async (apiKey: ApiKey) => {
    const modal = createModal(AsyncConfirmationModal);

    const rv = await modal({
      title: 'Delete API Key',
      confirmLabel: 'Delete',
      faIconName: 'trash',
      children: (
        <div>
          <p>
            <strong>Are you sure you want to delete the API Key &lsquo;{apiKey.key}&rsquo;?</strong>
          </p>
          <p>
            Once deleted, any tasks configured with this API Key may stop reporting progress to CloudReactor, or may not start at all.
          </p>
          <p>
            Please ensure no tasks are using this API Key.
          </p>
        </div>
      )
    });

    if (rv) {
      return await handleDeletionConfirmed(apiKey);
    }

    return null;
  };

  const handleDeletionConfirmed = async (apiKey: ApiKey) => {
    setFlashBody(null);

    try {
      await deleteApiKey(apiKey.uuid);

      setFlashAlertVariant('success');
      setFlashBody(`Successfully deleted API Key "${apiKey.key}".`);
      loadApiKeys();
    } catch (e) {
      setFlashAlertVariant('danger');
      setFlashBody(`Failed to deleted API Key "${apiKey.key}".`);
    }
  }

  const handleAddApiKey = (action: string | undefined, cbData: any) => {
    history.push('/api_keys/new')
  };

  const {
    q,
    currentPage
  } = getParams(location.search);

  return (
    <div className={styles.container}>
      {
        flashBody &&
        <Alert variant={flashAlertVariant || 'success'}>
          {flashBody}
        </Alert>
      }

      <Row>
        <Col>
          <BreadcrumbBar
            firstLevel="API Keys"
            secondLevel={null}
          />
        </Col>
      </Row>

      <Row>
        <Col xs={6} xl={4}>
          <Form.Control type="search" as={DebounceInput}
            className={classNames({
              'p-2': true,
              [styles.searchInput]: true
            })}
            onChange={handleQueryChanged}
            onKeyDown={keyEvent => {
              if (keyEvent.key === 'Enter') {
                loadApiKeys();
              }
            }}
            placeholder="Search API Keys"
            value={q}
          />
        </Col>
      </Row>

      {
        isLoading ? <Loading /> :
        (!q && (currentPage === 1) && (page.count === 0)) ?
        <p>You have no API keys.</p> : (
          <ApiKeyTable
            apiKeyPage={page}
            handlePageChanged={handlePageChanged}
            handleDeletionRequest={handleDeletionRequest}
          />
        )
      }

      {
        (accessLevel >= C.ACCESS_LEVEL_DEVELOPER) && (
          <Row>
            <Col>
              <CustomButton
                action="create"
                className="mt-3"
                faIconName="plus-square"
                label="Add new API Key ..."
                onActionRequested={handleAddApiKey}
                variant="outlined"
                size="small"
              />
            </Col>
          </Row>
        )
      }
    </div>
  );
}

export default abortableHoc(ApiKeyList);
