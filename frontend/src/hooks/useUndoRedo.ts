import { useState, useCallback, useRef, useMemo } from 'react';

export interface HistoryItem<T> {
  data: T;
  timestamp: number;
  description?: string;
}

export interface UndoRedoOptions {
  maxHistory?: number;
  enableDebounce?: boolean;
  debounceMs?: number;
}

export function useUndoRedo<T>(initialState: T, options: UndoRedoOptions = {}) {
  const {
    maxHistory = 50,
    enableDebounce = true,
    debounceMs = 500
  } = options;

  const [state, setState] = useState<T>(initialState);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  const initialTimestamp = useMemo(() => Date.now(), []);
  const historyRef = useRef<HistoryItem<T>[]>([{ data: initialState, timestamp: initialTimestamp }]);
  const currentIndexRef = useRef(0);
  const debounceTimerRef = useRef<number | null>(null);

  const updateCanStates = useCallback(() => {
    setCanUndo(currentIndexRef.current > 0);
    setCanRedo(currentIndexRef.current < historyRef.current.length - 1);
  }, []);

  const pushToHistory = useCallback((newState: T, description?: string) => {
    // Remove any states ahead of current position (redo stack)
    const newHistory = historyRef.current.slice(0, currentIndexRef.current + 1);

    // Add new state
    newHistory.push({
      data: newState,
      timestamp: Date.now(),
      description
    });

    // Trim history if it exceeds max size
    if (newHistory.length > maxHistory) {
      newHistory.shift();
    } else {
      currentIndexRef.current = newHistory.length - 1;
    }

    historyRef.current = newHistory;
    updateCanStates();
  }, [maxHistory, updateCanStates]);

  const debouncedPush = useCallback((newState: T, description?: string) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      pushToHistory(newState, description);
      debounceTimerRef.current = null;
    }, debounceMs);
  }, [debounceMs, pushToHistory]);

  const undo = useCallback(() => {
    if (currentIndexRef.current > 0) {
      currentIndexRef.current -= 1;
      const historyItem = historyRef.current[currentIndexRef.current];
      setState(historyItem.data);
      updateCanStates();
      return historyItem;
    }
    return null;
  }, [updateCanStates]);

  const redo = useCallback(() => {
    if (currentIndexRef.current < historyRef.current.length - 1) {
      currentIndexRef.current += 1;
      const historyItem = historyRef.current[currentIndexRef.current];
      setState(historyItem.data);
      updateCanStates();
      return historyItem;
    }
    return null;
  }, [updateCanStates]);

  const updateState = useCallback((newState: T | ((prev: T) => T), description?: string) => {
    const updatedState = typeof newState === 'function'
      ? (newState as (prev: T) => T)(state)
      : newState;

    setState(updatedState);

    if (enableDebounce) {
      debouncedPush(updatedState, description);
    } else {
      pushToHistory(updatedState, description);
    }
  }, [state, enableDebounce, debouncedPush, pushToHistory]);

  const clearHistory = useCallback(() => {
    historyRef.current = [{ data: state, timestamp: Date.now() }];
    currentIndexRef.current = 0;
    updateCanStates();
  }, [state, updateCanStates]);

  const getHistory = useCallback(() => {
    return {
      history: historyRef.current,
      currentIndex: currentIndexRef.current,
      canUndo: currentIndexRef.current > 0,
      canRedo: currentIndexRef.current < historyRef.current.length - 1
    };
  }, []);

  // Cleanup debounce timer on unmount
  const cleanup = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
  }, []);

  return {
    state,
    updateState,
    undo,
    redo,
    canUndo,
    canRedo,
    clearHistory,
    getHistory,
    cleanup
  };
}
