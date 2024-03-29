import _ from 'lodash';

import moment from 'moment';

import { NotificationMethod } from '../../../types/domain_types';
import { fetchNotificationMethods } from '../../../utils/api';
import { timeFormat } from '../../../utils/index';

import React, { Fragment } from 'react';

import { Link } from 'react-router-dom';

import {
  Card
} from 'react-bootstrap';

import * as path from '../../../constants/routes';

import { makeEntityList } from '../../../components/common/EntityList/EntityList';

import '../../../styles/cardStyles.scss';

const NotificationMethodList = makeEntityList<NotificationMethod>({
  entityName: 'Notification Method',
  fetchPage: ({ groupId, offset, maxResults, abortSignal }) => {
    return fetchNotificationMethods({
      groupId,
      offset,
      maxResults,
      abortSignal
    });
  },
  renderEntities: ({ page, handleSelection }) => {
    return (
      <Fragment>
        {
          (page?.results ?? []).map(method => {
            const updated = moment(method.updated_at);

            return (
              <Card
                key={method.uuid}
                className="custom_bg_hover"
              >
                <Card.Body>
                  <Card.Title>
                  {
                    <Link to={path.NOTIFICATION_METHODS + '/' + method.uuid}>
                      { method.name }
                    </Link>
                  }
                  </Card.Title>
                  <Card.Text>
                    {
                      method.run_environment ? (
                        <Link to={path.RUN_ENVIRONMENTS + '/' + method.run_environment.uuid}>
                          { method.run_environment.name }
                        </Link>
                      ) : <span>(Unscoped)</span>
                    }
                    <br/><br/>
                    <small className="text-muted">Associated {_.startCase(method.method_details.type)} Profile: {method.method_details.profile.name}</small>
                  </Card.Text>
                </Card.Body>
                <Card.Footer>
                  <small className="text-muted">Last updated {timeFormat(method.updated_at, true)} ({updated.fromNow()})</small>
                </Card.Footer>
              </Card>
            );
          })
        }
      </Fragment>
    );
  }
});

export default NotificationMethodList;