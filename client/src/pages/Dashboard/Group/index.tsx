import { Group } from '../../../types/website_types';

import React, { Fragment } from 'react';

import {
  Card
} from 'react-bootstrap';

import { makeEntityList } from '../../../components/common/EntityList/EntityList';

import '../../../styles/cardStyles.scss';

const GroupList = makeEntityList<Group>({
  entityName: 'Group',
  fetchPage: ({ context }) => {
    const {
      currentUser
    } = context;

    if (!currentUser) {
      return Promise.reject('Must be logged in to view Groups');
    }

    return Promise.resolve({
      count: currentUser.groups.length,
      results: currentUser.groups
    });
  },
  renderEntities: ({ page, handleSelection }) => {
    return (
      <Fragment>
        {
          (page?.results ?? []).map(group => {
            return (
              <Card
                  key={group.id}
                  className="custom_bg_hover"
                >
                  <Card.Body onClick={() => handleSelection(group.id)}>
                    <Card.Title>{group.name}</Card.Title>
                    <Card.Text>

                    </Card.Text>
                  </Card.Body>
                </Card>
            );
          })
        }
      </Fragment>
    );
  }
});

export default GroupList;