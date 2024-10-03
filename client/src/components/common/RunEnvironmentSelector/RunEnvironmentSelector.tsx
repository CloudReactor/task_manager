import _ from 'lodash';

import React, { Fragment, ReactNode } from 'react';

import { Checkbox, ListItemText, MenuItem, Select } from '@mui/material';

import styles from './RunEnvironmentSelector.module.scss';
import { RunEnvironment } from '../../../types/domain_types';

interface Props {
  runEnvironments: RunEnvironment[];
  selectedRunEnvironmentUuids?: string[];
  handleSelectedRunEnvironmentUuidsChanged: (uuids?: string[]) => void;
}

const ALL_RUN_ENVIRONMENTS = 'all';

const RunEnvironmentSelector = (props: Props) => {
  const { runEnvironments, selectedRunEnvironmentUuids } = props;

  const runEnvironmentsByUuid = _.keyBy(runEnvironments, 'uuid');

  const handleSelectedRunEnvironmentsInputChanged = (event: any, child?: ReactNode) => {
    let newSelectedRunEnvironmentUuids = event.target.value;

    if (_.isArray(newSelectedRunEnvironmentUuids)) {
      if (selectedRunEnvironmentUuids) {
        if (newSelectedRunEnvironmentUuids.includes(ALL_RUN_ENVIRONMENTS)) {
          newSelectedRunEnvironmentUuids = undefined
        }
      } else {
        newSelectedRunEnvironmentUuids = _.without(
          newSelectedRunEnvironmentUuids, ALL_RUN_ENVIRONMENTS);
      }
    }

    if (!newSelectedRunEnvironmentUuids || (newSelectedRunEnvironmentUuids.length === 0)) {
      newSelectedRunEnvironmentUuids = undefined
    }

    props.handleSelectedRunEnvironmentUuidsChanged(newSelectedRunEnvironmentUuids);
  };

  const selectValue = selectedRunEnvironmentUuids ?? [ALL_RUN_ENVIRONMENTS];

  return (
    <Select
     multiple={true} value={selectValue}
     onChange={handleSelectedRunEnvironmentsInputChanged}
     className={styles.runEnvironmentSelector}
     renderValue={(selected: unknown) => (
         <Fragment>
         {
           (selected as string[]).map(uuid =>
             ((uuid === 'all') ? 'Show all' : (runEnvironmentsByUuid[uuid]?.name ?? 'N/A'))
           ).join(', ')
         }
         </Fragment>
       )
     }
    >
      <MenuItem key={ALL_RUN_ENVIRONMENTS} value={ALL_RUN_ENVIRONMENTS}>
        <Checkbox checked={selectValue[0] === ALL_RUN_ENVIRONMENTS} />
        <ListItemText primary="Show all" />
      </MenuItem>
      {
        runEnvironments.map(runEnvironment => {
          return(
            <MenuItem key={runEnvironment.uuid} value={runEnvironment.uuid}>
              <Checkbox checked={selectedRunEnvironmentUuids?.includes(runEnvironment.uuid) ?? false} />
              <ListItemText primary={runEnvironment.name} />
            </MenuItem>
          );
        })
      }
    </Select>
  );
}

export default RunEnvironmentSelector;
