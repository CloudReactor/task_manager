import React, { FunctionComponent } from "react";
import classNames from 'classnames';
import styles from './Container.module.scss';

type LoadingProps = {
  style?: React.CSSProperties;
  type?: 'formContainer' | null;
}

const Container: FunctionComponent<LoadingProps> = ({style, type, children}) => {
  const styleProperties: React.CSSProperties = {...style};

  return (
    <div
      className={classNames({
        [styles.formContainer]: type === 'formContainer',
        [styles.container]: !type,
      })}
      style={styleProperties}
    >
      {children}
    </div>
  )
}

export default Container;