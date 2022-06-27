import React from "react";
import Container from './Container/Container';
import Svg from 'react-inlinesvg';
import styles from './loading.module.scss';

const Loading = () => {
  return (
    <Container
      style={{maxWidth: '500px', minWidth: '500px'}}
    >
      <div className={styles.loadingContainer}>
        <Svg
          src="/images/cloudreactor_logo_glyph.svg"
          description="CloudReactor Logo"
          className={styles.loadingSvg}
        />
        <div className={styles.text}>
          Loading...
        </div>
      </div>
    </Container>
  )
}

export default Loading;