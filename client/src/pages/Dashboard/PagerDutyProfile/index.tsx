import moment from 'moment';

import { PagerDutyProfile } from '../../../types/domain_types';
import { fetchPagerDutyProfiles } from '../../../utils/api';
import { timeFormat } from '../../../utils/index';

import React, { Fragment } from 'react';

import { Link } from 'react-router-dom';

import {
  Card
} from 'react-bootstrap';

import * as path from '../../../constants/routes';

import { makeEntityList } from '../../../components/common/EntityList/EntityList';

import '../../../styles/cardStyles.scss';

const PagerDutyProfileList = makeEntityList<PagerDutyProfile>({
  entityName: 'PagerDuty Profile',
  fetchPage: ({ groupId, offset, maxResults, abortSignal }) => {
    return fetchPagerDutyProfiles({
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
          (page?.results ?? []).map(profile => {
            const updated = moment(profile.updated_at);

            return (
              <Card
                key={profile.url}
                className="custom_bg_hover"
              >
                <Card.Body>
                  <Card.Title>
                  {
                    <Link to={path.PAGERDUTY_PROFILES + '/' + profile.uuid}>
                      { profile.name }
                    </Link>
                  }
                  </Card.Title>
                  <Card.Text>
                    {profile.description}
                    <br/><br/>
                    {
                      profile.run_environment ? (
                        <Link to={path.RUN_ENVIRONMENTS + '/' + profile.run_environment.uuid}>
                          { profile.run_environment.name }
                        </Link>
                      ) : <span>(Unscoped)</span>
                    }
                  </Card.Text>
                </Card.Body>
                <Card.Footer>
                  <small className="text-muted">Last updated {timeFormat(profile.updated_at, true)} ({updated.fromNow()})</small>
                </Card.Footer>
              </Card>
              );
          })
        }
      </Fragment>
    );
  }
});

export default PagerDutyProfileList;
