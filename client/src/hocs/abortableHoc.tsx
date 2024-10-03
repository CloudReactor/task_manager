import React, { useEffect, useState } from 'react';

export interface AbortSignalProps {
	abortSignal: AbortSignal;
}

export default function abortableHoc<P>(WrappedComponent: React.ComponentType<React.PropsWithChildren<P & AbortSignalProps>>): React.ComponentType<React.PropsWithChildren<P>> {
  const AbortableComponent = (props: P) => {
    const [abortController, setAbortController] = useState(new AbortController());

    useEffect(() => {
      return () => abortController.abort('Operation canceled after component unmounted');
    }, []);

    return <WrappedComponent abortSignal={abortController.signal} {...props} />;
  };

  return AbortableComponent;
}
