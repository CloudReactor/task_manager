import { Inflectors } from "en-inflectors";

import React from 'react';

import {
  Button,
  Tooltip
} from '@mui/material';

interface Props {
	cbData?: any,
  onActionRequested?: (action: string | undefined, cbData: any) => any;
  action?: string;
  faIconName?: string;
  label?: string;
  disabled?: boolean;
  inProgress?: boolean;
  inProgressFaIconName?: string;
  inProgressLabel?: string;
  variant?: 'contained' | 'outlined' | 'text';
  size?: 'small' | 'medium' | 'large';
  color?: 'primary' | 'secondary';
  tooltip?: string;
  className?: string;
  style?: any;
}

const ActionButton = (p: Props) => {
  const iconName = p.inProgress ?
      ((p.inProgressFaIconName || 'circle-notch') + ' fa-spin') :
      p.faIconName;
  const label = p.inProgress ?
    (p.inProgressLabel ??
     (p.label ? new Inflectors(p.label).toGerund() : '')) :
    p.label;

  return (
    <Tooltip title={p.tooltip || ''}>
      <span>
        <Button
          className={'action-button ' + (p.className ?? '')}
          style={p.style ?? {}}
          size={ p.size ?? 'small' }
          variant={ p.variant ?? 'outlined' }
          color={ p.color ?? 'grey' }
          disabled={(p.disabled ?? false) && !p.inProgress}
          onClick={() => p.onActionRequested && p.onActionRequested(p.action, p.cbData)}>
          { iconName && <i className={'fas fa-' + iconName + ' pl-1 pr-1'} /> }
          { label }
        </Button>
      </span>
    </Tooltip>
  );
};

export default ActionButton;
