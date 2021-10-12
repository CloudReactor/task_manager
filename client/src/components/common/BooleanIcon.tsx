import React from 'react';

interface Props {
  checked: boolean | null;
}

const BooleanIcon = (p: Props) => (
  p.checked ? <i className="fas fa-check" /> : <i className="fas fa-times" />
);

export default BooleanIcon;