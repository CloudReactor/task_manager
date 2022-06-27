import React from 'react';
import axios, { CancelToken } from 'axios';

export interface CancelTokenProps {
	cancelToken: CancelToken;
}

export default function cancelTokenHoc(Component: React.ComponentType<any>): React.ComponentClass<any> {
  return class extends React.Component {
    source = axios.CancelToken.source();

    componentWillUnmount() {
      this.source.cancel('Operation cancelled after component unmounted');
    }

    render() {
      return <Component cancelToken={this.source.token} {...this.props} />;
    }
  };
}