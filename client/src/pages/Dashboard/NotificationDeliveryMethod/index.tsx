import _ from 'lodash';

import moment from 'moment';

import { NotificationDeliveryMethod } from '../../../types/domain_types';
import { fetchNotificationDeliveryMethods } from '../../../utils/api';
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

const NotificationDeliveryMethodList = makeEntityList<NotificationDeliveryMethod>({
  entityName: 'Notification Delivery Method',
  fetchPage: ({ groupId, offset, maxResults, abortSignal }) => {
    return fetchNotificationDeliveryMethods({
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
          (page?.results ?? []).map(method => {
            const updated = moment(method.updated_at);
            // Backend now returns "email" or "pager_duty"
            const getDisplayType = (fullType?: string): string => {
              if (!fullType) return 'Unknown';
              if (fullType === 'email') return 'Email';
              if (fullType === 'pager_duty') return 'PagerDuty';
              return _.startCase(fullType);
            };
            const methodType = getDisplayType(method.delivery_method_type);

            return (
              <Col key={method.uuid} sm={12} md={6} lg={4} className="mb-3">
                <Card className="custom_bg_hover h-100">
                  <Card.Body>
                    <Card.Title>
                    {
                      <Link to={path.NOTIFICATION_DELIVERY_METHODS + '/' + method.uuid}>
                        { method.name }
                      </Link>
                    }
                    {' '}
                    <Badge variant="info">{methodType}</Badge>
                    </Card.Title>
                    <Card.Text>
                      {
                        method.run_environment ? (
                          <Link to={path.RUN_ENVIRONMENTS + '/' + method.run_environment.uuid}>
                            { method.run_environment.name }
                          </Link>
                        ) : <span>(Unscoped)</span>
                      }
                      {method.description && (
                        <>
                          <br/><br/>
                          {method.description}
                        </>
                      )}
                    </Card.Text>
                  </Card.Body>
                  <Card.Footer>
                    <small className="text-muted">Last updated {timeFormat(method.updated_at, true)} ({updated.fromNow()})</small>
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

export default NotificationDeliveryMethodList;
