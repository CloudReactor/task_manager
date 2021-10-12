import pluralize from "pluralize";

import React from "react";

import {
  Alert,
  Container
} from 'react-bootstrap';

interface Props {
  count: number;
  itemName: string;
}

const FailureCountAlert = (p: Props) =>
  p.count ? (
    <Container fluid style={{ padding: 0}}>
    	<Alert variant="danger">
        {p.count} { pluralize (p.itemName, p.count)} { pluralize ('has', p.count)} failed or timed out -- see below for further details
    	</Alert>
    </Container>
  ) : null;

export default FailureCountAlert;
