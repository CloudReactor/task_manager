import moment from 'moment';

import { RunEnvironment } from '../../../types/domain_types';
import { fetchRunEnvironments } from '../../../utils/api';
import { timeFormat } from '../../../utils/index';
import { ACCESS_LEVEL_DEVELOPER } from '../../../utils/constants';

import React, { Fragment } from 'react';

import {
  Card
} from 'react-bootstrap';

import { makeEntityList } from '../../../components/common/EntityList/EntityList';

import '../../../styles/cardStyles.scss';

const RunEnvironmentList = makeEntityList<RunEnvironment>({
  entityName: 'Run Environment',
  minAccessLevelToViewDetails: ACCESS_LEVEL_DEVELOPER,
  fetchPage: ({ groupId, offset, maxResults, cancelToken }) => {
    return fetchRunEnvironments({
      groupId,
      offset,
      maxResults,
      cancelToken
    });
  },
  renderEntities: ({ page, handleSelection }) => {
    return (
      <Fragment>
        {
          (page?.results ?? []).map(runEnvironment => {
            const updated = moment(runEnvironment.updated_at);
            return (
              <Card
                  key={runEnvironment.uuid}
                  className="custom_bg_hover"
                >
                <Card.Body onClick={() => handleSelection(runEnvironment.uuid)}>
                  <Card.Title>{runEnvironment.name}</Card.Title>
                  <Card.Text>{runEnvironment.description}</Card.Text>
                </Card.Body>
                <Card.Footer>
                  <small className="text-muted">
                    Last updated {timeFormat(runEnvironment.updated_at, true)} ({updated.fromNow()})
                  </small>
                </Card.Footer>
              </Card>
            );
          })
        }
      </Fragment>
    );
  }
});

export default RunEnvironmentList;
