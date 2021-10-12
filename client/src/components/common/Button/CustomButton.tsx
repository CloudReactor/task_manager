import React from 'react';
import classNames from 'classnames';
import styles from './CustomButton.module.scss';

interface Props {
  action?: string;
  onActionRequested?: (action: string | undefined, cbData: any) => any;
  cbData?: any,
  className?: any;
  color?: "primary" | "secondary" | "danger";
  component?: 'div';
  disabled?: boolean;
  faIconName?: string;
  fullWidth?: boolean;
  href?: string;
  inProgress?: boolean;
  inProgressFaIconName?: string;
  label?: string;
  isLoading?: boolean;
  size?: 'small';
  type?: "submit" | "button" | "reset";
  variant?: 'solid' | 'outlined';
}

const CustomButton = ({
  className,
  color,
  disabled,
  faIconName,
  fullWidth,
  href,
  inProgress,
  inProgressFaIconName,
  isLoading,
  label = 'Submit',
  variant,
  size,
  ...props
}: Props) => {

  // if href is provided, component shold be a div with an href. Else, button
  const Component = href ? 'div' : 'button';

  // if user hasn't provided inProgress prop or an faIconName, iconName will be undefined. No icon will be shown
  const iconName = inProgress ? ((inProgressFaIconName || 'circle-notch') + ' fa-spin') : faIconName;

  return (
    <div className={classNames({
      [styles.buttonContainer]: true,
      [styles.noMargin]: className === 'noMargin',
    })}>
      <Component
        type={props.type}
        className={classNames({
          [styles.button]: true,
          [styles.small]: size === 'small',
          [styles.outlined]: variant === 'outlined',
          [styles.primary]: color === 'primary',
          [styles.secondary]: color === 'secondary',
          [styles.danger]: color === 'danger',
          [styles.fullWidth]: !!fullWidth,
          [className]: !!className,
        })}
        disabled={disabled}
        onClick={() => props.onActionRequested && props.onActionRequested(props.action, props.cbData)}
      >
        {/* if href is provided, Component will be a div; return the enclosed <a> here */}
        { href &&<a href={href} target="_blank" rel="noopener noreferrer">{label}</a> }
        { iconName && <i className={'fas fa-' + iconName + ' mr-2'} /> }
        {/* if href is not provided, Component should be a button; return the button label text (no <a>) here */}
        { !href && <span>{inProgress ? 'Saving' : label}</span> }

      </Component>
    </div>
  );
}

export default CustomButton;