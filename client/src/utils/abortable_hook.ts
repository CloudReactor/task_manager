import { useEffect, DependencyList } from 'react';

function makeAbortable<T>(cb: (abortSignal: AbortSignal) => Promise<T>,
    deps?: DependencyList) {
  useEffect(() => {
    const abortController = new AbortController();
    cb(abortController.signal);

    return () => {
      abortController.abort('Operation canceled after unmounting');
    };

  }, deps ?? []);
}

export default makeAbortable;
