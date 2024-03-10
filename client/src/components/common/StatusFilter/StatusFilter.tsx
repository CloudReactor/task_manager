import _ from 'lodash';

import React, { Fragment, ReactNode } from 'react';

import { Checkbox, ListItemText, MenuItem, Select } from '@material-ui/core';

import { TASK_EXECUTION_STATUSES } from '../../../utils/constants';

import styles from './StatusFilter.module.scss';

interface Props {
  selectedStatuses?: string[];
  handleSelectedStatusesChanged: (statuses?: string[]) => void;
}

const ANY_STATUS = 'any';

const StatusFilter = (props: Props) => {
  const { selectedStatuses } = props;

  const handleSelectedStatusesInputChanged = (event: any, child?: ReactNode) => {
    let newSelectedStatuses = event.target.value;

    if (_.isArray(newSelectedStatuses)) {
      if (selectedStatuses) {
        if (newSelectedStatuses.includes(ANY_STATUS)) {
          newSelectedStatuses = undefined
        }
      } else {
        newSelectedStatuses = _.without(newSelectedStatuses, ANY_STATUS);
      }
    }

    if (!newSelectedStatuses || (newSelectedStatuses.length === 0)) {
      newSelectedStatuses = undefined
    }

    props.handleSelectedStatusesChanged(newSelectedStatuses);
  };

  const ss = selectedStatuses ?? [ANY_STATUS];

  return (
    <Select
     multiple={true} value={ss}
     onChange={handleSelectedStatusesInputChanged}
     className={styles.statusFilter}
     renderValue={(selected: unknown) =>
      <Fragment>
        {(selected as string[]).map(s => _.startCase(s.toLowerCase())).join(', ')}
      </Fragment>
    }
    >
      <MenuItem key={ANY_STATUS} value={ANY_STATUS}>
        <Checkbox checked={ss[0] === ANY_STATUS} />
        <ListItemText primary="Show all" />
      </MenuItem>
      {
        TASK_EXECUTION_STATUSES.map(status => {
          return(
            <MenuItem key={status} value={status}>
              <Checkbox checked={selectedStatuses ? selectedStatuses.includes(status) : false} />
              <ListItemText primary={_.startCase(status.toLowerCase())} />
            </MenuItem>
          );
        })
      }
    </Select>
  );
}

export default StatusFilter;