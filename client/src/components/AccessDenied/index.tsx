import React from "react";
import Container from '../Container/Container';

const AccessDenied = () => {
  return (
    <Container
      style={{maxWidth: '500px', minWidth: '500px'}}
    >
    <div>
      You don&apos;t have access to this page.
      Try logging in again.
    </div>
    </Container>
  )
}

export default AccessDenied;