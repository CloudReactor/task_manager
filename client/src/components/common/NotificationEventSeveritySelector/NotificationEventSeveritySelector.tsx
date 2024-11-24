import _ from 'lodash';

import React, { Fragment, ReactNode } from 'react';

import { Checkbox, ListItemText, MenuItem, Select } from '@mui/material';

import {
  NOTIFICATION_EVENT_SEVERITIES,
  NOTIFICATION_EVENT_SEVERITY_TO_LABEL
} from '../../../utils/constants';

import styles from './NotificationEventSeveritySelector.module.scss';

interface Props {
  selectedSeverity?: number | null,
  disabled?: boolean,
  onSelectedSeverityChanged: (severity?: number | null) => void;
}

const NotificationEventSeveritySelector = (props: Props) => {
  const { selectedSeverity } = props;

  const handleSelectedSeverityInputChanged = (event: any, child?: ReactNode) => {
    let newSelectedSeverity = event.target.value;

    if (!newSelectedSeverity) {
      newSelectedSeverity = null;
    }

    props.onSelectedSeverityChanged(newSelectedSeverity);
  };


  return (
    <Select className={styles.selector}
     disabled={props.disabled ?? false}
     value={selectedSeverity ?? ''}
     onChange={handleSelectedSeverityInputChanged}
     autoWidth={true} displayEmpty={true}
     >
      <MenuItem key="" value="">
        <ListItemText primary="None" />
      </MenuItem>
      {
        NOTIFICATION_EVENT_SEVERITIES.map(severity => {
          return (
            <MenuItem key={severity} value={severity}>
              <ListItemText primary={_.startCase(NOTIFICATION_EVENT_SEVERITY_TO_LABEL[severity])} />
            </MenuItem>
          );
        })
      }
    </Select>
  );
};

export default NotificationEventSeveritySelector;