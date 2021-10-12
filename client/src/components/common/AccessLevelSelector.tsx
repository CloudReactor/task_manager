import {
  ACCESS_LEVEL_ADMIN,
  ACCESS_LEVEL_TO_ROLE_NAME
} from '../../utils/constants';

import React from 'react';

import {
  Form,
} from 'react-bootstrap';

interface Props {
  maxAccessLevel?: number;
  [propName: string]: any;
}

const AccessLevelSelector = (p: Props) => {
  const {
    maxAccessLevel = ACCESS_LEVEL_ADMIN,
    ...passThroughProps
  } = p;

  return (
    <Form.Control className="mb-2 mr-sm-2" as="select" {...passThroughProps}>
      {
        Object.entries(ACCESS_LEVEL_TO_ROLE_NAME)
          .filter(([accessLevel, roleName]) => (Number(accessLevel) <= maxAccessLevel))
          .map(([accessLevel, roleName]) => (
            <option key={accessLevel} value={accessLevel}>{roleName}</option>
          ))
      }
    </Form.Control>
  );
};

export default AccessLevelSelector;