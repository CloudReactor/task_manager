import _ from 'lodash';
import axios from 'axios';

import * as C from '../../../utils/constants';

import { ApiKey } from '../../../types/domain_types';

import {
  deleteApiKey,
  fetchApiKeys,
  ResultsPage
} from "../../../utils/api";

import React, { Component } from "react";
import { RouteComponentProps, withRouter } from "react-router";

import { Alert, Row, Col } from 'react-bootstrap';

import { createModal } from 'react-modal-promise';

import cancelTokenHoc, { CancelTokenProps } from '../../../hocs/cancelTokenHoc';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import AsyncConfirmationModal from '../../../components/common/AsyncConfirmationModal';

import { BootstrapVariant } from '../../../types/ui_types';
import * as UIC from '../../../utils/ui_constants';

import Loading from '../../../components/Loading';
import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import CustomButton from '../../../components/common/Button/CustomButton';
import ApiKeyTable from "../../../components/ApiKeyList/ApiKeyTable";
import { getParams, setURL } from '../../../utils/url_search';

import classNames from 'classnames';
import styles from './index.module.scss'

interface Props extends RouteComponentProps<any> {
}

type InnerProps = Props & CancelTokenProps;

interface State {
  isLoading: boolean;
  flashBody?: any;
  flashAlertVariant?: BootstrapVariant;
  apiKeyPage: ResultsPage<ApiKey>;
  currentPage: number;
  rowsPerPage: number;
}

class ApiKeyList extends Component<InnerProps, State> {
  static contextType = GlobalContext;

  constructor(props: InnerProps) {
    super(props);

    this.state = {
      isLoading: false,
      apiKeyPage: { count: 0, results: [] },
      currentPage: 0,
      rowsPerPage: UIC.DEFAULT_PAGE_SIZE,
    };

    this.loadApiKeys = _.debounce(this.loadApiKeys, 250);
  }

  loadApiKeys = async (): Promise<void> => {
    const { currentGroup } = this.context;

    const {
      currentPage,
      rowsPerPage
    } = this.state;

    // get params from URL
    const { q } = getParams(this.props.location.search);

    // user can't sort API keys, so just set here
    const sortBy = 'key';
    const descending = false;
    const offset = currentPage * rowsPerPage;

    let apiKeyPage: any = [];

    this.setState({
      isLoading: true
    });

    try {
      apiKeyPage = await fetchApiKeys({
        groupId: currentGroup?.id,
        q,
        sortBy,
        descending,
        offset,
        maxResults: rowsPerPage,
        cancelToken: this.props.cancelToken
      });
    } catch (error) {
      if (axios.isCancel(error)) {
        console.log('Request cancelled: ' + error.message);
        return;
      }
    }

    this.setState({
      isLoading: false,
      apiKeyPage
    });
  }

  handleSelectItemsPerPage = (
    event: React.ChangeEvent<HTMLSelectElement>
  ): void => {
    const value = event.target.value;
    this.setState({
      rowsPerPage: parseInt(value)
    }, this.loadApiKeys);
  };

  handleSortChanged = async (ordering?: string, toggleDirection?: boolean) => {
    // this.setURL(undefined, ordering, toggleDirection);
    // this.loadApiKeys();
  };

  handleQueryChanged = (
    event: React.ChangeEvent<HTMLInputElement>
  ): void => {
    setURL(this.props.location, this.props.history, event.target.value, 'q');
    this.loadApiKeys();
  };

  handlePageChanged = (currentPage: number): void => {
    this.setState({ currentPage }, this.loadApiKeys);
  }

  handlePrev = (): void =>
    this.setState({
      currentPage: Math.max(this.state.currentPage - 1, 0)
    }, this.loadApiKeys);

  handleNext = (): void =>
    this.setState({
      currentPage: this.state.currentPage + 1
    }, this.loadApiKeys);

  componentDidMount() {
    this.loadApiKeys();
  }

  public render() {
    const {
      apiKeyPage,
      currentPage,
      isLoading,
      flashBody,
      flashAlertVariant,
    } = this.state;

    const accessLevel = accessLevelForCurrentGroup(this.context);

    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return null;
    }

    // initialise page based on URL query parameters. Destructure with defaults, otherwise typescript throws error
    const {q = '', sortBy = '', descending = false} = getParams(
      this.props.location.search);

    return (
      <div key="aktcon" className={styles.container}>
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
          <Col>
            <input key="searchInput"
              className={classNames({
                'p-2': true,
                [styles.searchInput]: true
              })}
              onChange={this.handleQueryChanged}
              onKeyDown={keyEvent => {
                if (keyEvent.key === 'Enter') {
                  this.loadApiKeys();
                }
              }}
              placeholder="Search"
              value={q}
            />
          </Col>
        </Row>

        {
          isLoading ? <Loading /> :
          (!q && (currentPage === 0) && (apiKeyPage.count === 0)) ?
          <p>You have no API keys.</p> : (
            <ApiKeyTable
              q={q}
              sortBy={sortBy}
              descending={descending}
              handleSortChanged={this.handleSortChanged}
              loadApiKeys={this.loadApiKeys}
              handlePageChanged={this.handlePageChanged}
              handleSelectItemsPerPage={this.handleSelectItemsPerPage}
              handleDeletionRequest={this.handleDeletionRequest}
              {... this.state}
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
                  onActionRequested={this.handleAddApiKey}
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

  private handleDeletionRequest = async (apiKey: ApiKey) => {
    const modal = createModal(AsyncConfirmationModal);

    const rv = await modal({
      title: 'Delete API Key',
      confirmLabel: 'Delete',
      faIconName: 'trash',
      children: (
        <div>
          <p>
            <strong>Are you sure you want to delete the API Key '{apiKey.key}'?</strong>
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
      return await this.handleDeletionConfirmed(apiKey);
    }

    return Promise.resolve(null);
  };

  private handleDeletionConfirmed = async (apiKey: ApiKey) => {
    this.setState({
      flashBody: null
    });

    try {
      await deleteApiKey(apiKey.uuid);

      this.setState({
        flashAlertVariant: 'success',
        flashBody: `Successfully deleted API Key "${apiKey.key}".`
      }, () => this.loadApiKeys());
    } catch (e) {
      this.setState({
        flashAlertVariant: 'danger',
        flashBody: `Failed to deleted API Key "${apiKey.key}".`
      });
    }
  }

  handleAddApiKey = (action: String | undefined, cbData: any) => {
    this.props.history.push('/api_keys/new')
  };
}

export default withRouter(cancelTokenHoc(ApiKeyList));