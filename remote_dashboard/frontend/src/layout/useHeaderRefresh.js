import { useCallback, useEffect, useRef } from 'react';
import { useOutletContext } from 'react-router-dom';

function useHeaderRefresh(onRefresh, busy = false, enabled = true) {
  const { setHeaderAction } = useOutletContext();
  const refreshRef = useRef(onRefresh);

  useEffect(() => {
    refreshRef.current = onRefresh;
  }, [onRefresh]);

  const handleRefresh = useCallback(() => {
    refreshRef.current?.();
  }, []);

  useEffect(() => {
    if (!setHeaderAction) return undefined;

    if (!enabled) {
      setHeaderAction(null);
      return () => setHeaderAction(null);
    }

    setHeaderAction({
      label: 'Atualizar',
      busy,
      onClick: handleRefresh,
    });

    return () => setHeaderAction(null);
  }, [busy, enabled, handleRefresh, setHeaderAction]);
}

export default useHeaderRefresh;
