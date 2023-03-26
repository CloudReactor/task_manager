import { useEffect, DependencyList } from 'react';
import axios, { CancelToken } from 'axios';

function useAxiosCleanup<T>(cb: (cancelToken: CancelToken) => Promise<T>,
    deps?: DependencyList) {
  useEffect(() => {
    const source = axios.CancelToken.source();
    cb(source.token);

    return () => {
      source.cancel('Operation cancelled after unmounting');
    };

  }, deps ?? []);
}

export default useAxiosCleanup;
