import React from 'react';

export interface AbortSignalProps {
	abortSignal: AbortSignal;
}

export default function abortableHoc(Component: React.ComponentType<any>): React.ComponentClass<any> {
  class AbortableComponent extends React.Component {
    abortController = new AbortController();

    componentWillUnmount() {
      this.abortController.abort('Operation cancelled after component unmounted');
    }

    render() {
      return <Component abortSignal={this.abortController.signal} {...this.props} />;
    }
  };

  return AbortableComponent;
}