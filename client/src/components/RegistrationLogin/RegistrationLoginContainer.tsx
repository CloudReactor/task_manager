import React from 'react';
import Svg from 'react-inlinesvg';
import styles from './RegistrationLoginContainer.module.scss';

interface Props {
  children: React.ReactNode;
  heading: string;
}

const RegistrationLoginContainer = (props: Props) => {

  return (
    <div className={styles.container}>
      <div className={styles.logo}>
        <Svg
          src="/images/cloudreactor_logo_light.svg"
          description="CloudReactor Logo"
        />
      </div>
      <h1>{props.heading}</h1>
      {props.children}
    </div>
  );
}

export default RegistrationLoginContainer;