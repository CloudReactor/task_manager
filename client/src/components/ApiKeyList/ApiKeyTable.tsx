import {
  ACCESS_LEVEL_TO_ROLE_NAME
} from '../../utils/constants';

import { ApiKey } from '../../types/domain_types';
import { ResultsPage } from '../../utils/api';

import React, { Fragment, useState } from 'react';

import { Link } from 'react-router-dom'

import { Button, ButtonGroup, ButtonToolbar, Row, Col, Toast } from 'react-bootstrap'

import BootstrapTable from 'react-bootstrap-table-nextgen';

import CopyToClipboard from 'react-copy-to-clipboard';

import BooleanIcon from '../../components/common/BooleanIcon';

import './ApiKeyTable.css'
import styles from './ApiKeyTable.module.scss';

interface Props {
  apiKeyPage: ResultsPage<ApiKey>;
  handlePageChanged: (currentPage: number) => void;
  handleDeletionRequest: (apiKey: ApiKey) => void;
}

const ApiKeyTable = ({
  apiKeyPage,
  handleDeletionRequest
}: Props) => {
  const [keyCopiedAt, setKeyCopiedAt] = useState(null as number | null);

  const columns = [{
    dataField: 'uuid',
    text: 'UUID',
    hidden: true
  }, {
    dataField: 'name',
    text: 'Name',
    formatter:  (name: string, apiKey: ApiKey, rowIndex: number, extraData: any) => (
      <Link to={'/api_keys/' + encodeURIComponent(apiKey.uuid)}>
        { name || '(Unnamed)' }
      </Link>
    )
  }, {
    dataField: 'key',
    classes: `${styles.test}`,
    text: 'Key',
    formatter: (key: string, apiKey: ApiKey, rowIndex: number, extraData: any) => (
      <div className="d-sm-inline-flex justify-content-between align-items-center w-100">
        <span className="text-monospace">{ key }</span>
        <span className="ml-2">
          <CopyToClipboard text={key}
            onCopy={(text: string, copied: boolean) => {
              if (copied) {
                setKeyCopiedAt(new Date().getTime());
              }
            }}>
            <Button size="sm" variant="outline-secondary">
              <i className="fas fa-clipboard"/>
            </Button>
          </CopyToClipboard>
        </span>
      </div>
    )
  }, {
    dataField: 'access_level',
    text: 'Access Level',
    formatter: (accessLevel: number, apiKey: ApiKey, rowIndex: number, extraData: any) => (
      <Fragment>{ ACCESS_LEVEL_TO_ROLE_NAME[accessLevel] }</Fragment>
    )
  },  {
    dataField: 'enabled',
    text: 'Enabled',
    formatter: (enabled: boolean, apiKey: ApiKey, rowIndex: number, extraData: any) => (
      <BooleanIcon checked={enabled} />
    ),
    align: 'center'
  }, {
    dataField: 'run_environment.uuid',
    text: 'Run Environment',
    formatter: (uuid: string | null, apiKey: ApiKey, rowIndex: number, extraData: any) => (
      uuid ? (
        <Link to={'/run_environments/' + encodeURIComponent(uuid)}>{ apiKey.run_environment?.name }</Link>
      ) : 'Any'
    ),
  }, {
    dataField: 'group',
    text: 'Group',
    formatter: (group: any, apiKey: ApiKey, rowIndex: number, extraData: any) => (
      <Link to={'/groups/' + encodeURIComponent(apiKey.group.id)}>{ apiKey.group.name }</Link>
    ),
  }, {
    dataField: 'uuid',
    text: 'Actions',
    formatter: (uuid: string, apiKey: ApiKey, rowIndex: number, extraData: any) => (
      <ButtonToolbar>
        <ButtonGroup size="sm" className="mr-2">
          <Button>
            <Link to={'/api_keys/' + encodeURIComponent(uuid)}>
              <i className="fa fa-wrench" />&nbsp;
              <span className="d-none d-xl-inline">Modify</span>
            </Link>
          </Button>

          <Button onClick={() => {
              handleDeletionRequest(apiKey);
            }}>
            <i className="fa fa-trash" /><span className="d-none d-xl-inline"> Delete</span>
          </Button>
        </ButtonGroup>
      </ButtonToolbar>
    ),
    editable: false,
  }];

  return (
    <div className={styles.container}>
      <Row>
        <Col>
          <BootstrapTable
            keyField='uuid'
            classes={styles.tableContainer}
            data={apiKeyPage.results}
            columns={columns}
            striped={true}
            bootstrap4={true}
            wrapperClasses="table-responsive"
          />
        </Col>
      </Row>

      <Toast onClose={() => { setKeyCopiedAt(null); } }
        show={!!keyCopiedAt} delay={3000} autohide
        style={{
          position: 'absolute',
          bottom: 0,
          right: 0,
        }}>
        <Toast.Header>
          Key copied!
        </Toast.Header>
        <Toast.Body>The API Key was copied to your clipboard.</Toast.Body>
      </Toast>
    </div>
  );
}

export default ApiKeyTable;
