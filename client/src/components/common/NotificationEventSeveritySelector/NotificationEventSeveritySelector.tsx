import _ from 'lodash';

import React, { Fragment, ReactNode } from 'react';

import { Checkbox, ListItemText, MenuItem, Select } from '@mui/material';

import {
  NOTIFICATION_EVENT_SEVERITIES,
  NOTIFICATION_EVENT_SEVERITY_TO_LABEL,
  NOTIFICATION_EVENT_SEVERITY_LABEL_TO_VALUE
} from '../../../utils/constants';

import styles from './NotificationEventSeveritySelector.module.scss';

interface Props {
  selectedSeverity?: number | string | null,
  disabled?: boolean,
  onSelectedSeverityChanged: (severity?: number) => void;
}

const toNumericSeverity = (x: any): number | undefined => {
  if (typeof x === 'number') {
    return x;
  }
  
  if (typeof x === 'string') {
    const lower = x.toLowerCase();
    const v = NOTIFICATION_EVENT_SEVERITY_LABEL_TO_VALUE[lower];
    if (v) {
      return v;
    }
    const parsed = parseInt(x, 10);
    if (!isNaN(parsed)) {
      return parsed;
    }
  }

  console.log('toNumericSeverity: unable to convert severity:', x);

  return undefined;
};    

const NotificationEventSeveritySelector = (props: Props) => {
  const { selectedSeverity } = props;


  const handleSelectedSeverityInputChanged = (event: any, child?: ReactNode) => {
    const newSelectedSeverity = event.target.value;
    
    if (!newSelectedSeverity) {
      props.onSelectedSeverityChanged(undefined);
      return;        
    }

    props.onSelectedSeverityChanged(toNumericSeverity(newSelectedSeverity));
  };

  console.log('NotificationEventSeveritySelector', selectedSeverity, typeof selectedSeverity);
  console.dir(selectedSeverity)

  const valueToUse = toNumericSeverity(selectedSeverity);

  // If selectedSeverity is a number but not in NOTIFICATION_EVENT_SEVERITIES, show it as a custom option
  const isCustom = typeof selectedSeverity === 'number' && !NOTIFICATION_EVENT_SEVERITIES.includes(selectedSeverity);

  return (
    <Select className={styles.selector}
     disabled={props.disabled ?? false}
     value={valueToUse ?? ''}
     onChange={handleSelectedSeverityInputChanged}
     autoWidth={false}
     displayEmpty={true}
     size="small"
     >
      <MenuItem key="" value="">
        <ListItemText primary="Any" />
      </MenuItem>
      {
        NOTIFICATION_EVENT_SEVERITIES.map(severity => (
          <MenuItem key={severity} value={severity}>
            <ListItemText primary={_.startCase(NOTIFICATION_EVENT_SEVERITY_TO_LABEL[severity])} />
          </MenuItem>
        ))
      }
      {isCustom && (
        <MenuItem key={selectedSeverity} value={selectedSeverity}>
          <ListItemText primary={`Custom (${selectedSeverity})`} />
        </MenuItem>
      )}
    </Select>
  );
};

export default NotificationEventSeveritySelector;