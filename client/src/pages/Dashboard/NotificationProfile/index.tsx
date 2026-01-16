import moment from 'moment';

import { NotificationProfile } from '../../../types/domain_types';
import { fetchNotificationProfiles } from '../../../utils/api';
import { timeFormat } from '../../../utils/index';

import React, { Fragment } from 'react';

import { Link } from 'react-router-dom';

import {
  Card,
  Badge,
  Row,
  Col
} from 'react-bootstrap';

import * as path from '../../../constants/routes';

import { makeEntityList } from '../../../components/common/EntityList/EntityList';

import '../../../styles/cardStyles.scss';

const NotificationProfileList = makeEntityList<NotificationProfile>({
  entityName: 'Notification Profile',
  fetchPage: ({ groupId, offset, maxResults, abortSignal }) => {
    return fetchNotificationProfiles({
      groupId,
      offset,
      maxResults,
      abortSignal
    });
  },
  renderEntities: ({ page, handleSelection }) => {
    return (
      <Row>
        {
          (page?.results ?? []).map(profile => {
            const updated = moment(profile.updated_at);

            return (
              <Col key={profile.uuid} sm={12} md={6} lg={4} className="mb-3">
                <Card className="custom_bg_hover h-100 d-flex flex-column">
                  <Card.Body className="flex-grow-1">
                    <Card.Title>
                    {
                      <Link to={path.NOTIFICATION_PROFILES + '/' + profile.uuid}>
                        { profile.name }
                      </Link>
                    }
                    {' '}
                    {profile.enabled ? (
                      <Badge variant="success">Enabled</Badge>
                    ) : (
                      <Badge variant="secondary">Disabled</Badge>
                    )}
                    </Card.Title>
                    <Card.Text>
                      {
                        profile.run_environment ? (
                          <Link to={path.RUN_ENVIRONMENTS + '/' + profile.run_environment.uuid}>
                            { profile.run_environment.name }
                          </Link>
                        ) : <Badge variant="secondary">Unscoped</Badge>
                      }
                      <br/>
                      {profile.notification_delivery_methods.length > 0 ? (
                        <small className="text-muted">
                          {profile.notification_delivery_methods.map((method, index) => (
                            <Fragment key={method.uuid}>
                              {index > 0 && ', '}
                              <Link to={path.NOTIFICATION_DELIVERY_METHODS + '/' + method.uuid}>
                                {method.name}
                              </Link>
                            </Fragment>
                          ))}
                        </small>
                      ) : (
                        <small className="text-muted">No delivery methods</small>
                      )}
                    </Card.Text>
                  </Card.Body>
                  <Card.Footer>
                    <small className="text-muted">Last updated {timeFormat(profile.updated_at, true)} ({updated.fromNow()})</small>
                  </Card.Footer>
                </Card>
              </Col>
            );
          })
        }
      </Row>
    );
  }
});

export default NotificationProfileList;
