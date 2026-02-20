/**
 * Tests for useUndoRedo hook
 */

import { renderHook, act } from '@testing-library/react';
import { useUndoRedo } from './useUndoRedo';

describe('useUndoRedo Hook', () => {
  describe('Basic Functionality', () => {
    test('initializes with provided state', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));
      expect(result.current.state).toBe('initial');
    });

    test('canUndo and canRedo are initially false', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));
      expect(result.current.canUndo).toBe(false);
      expect(result.current.canRedo).toBe(false);
    });

    test('updates state when updateState is called', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('new state', 'Test update');
      });

      expect(result.current.state).toBe('new state');
    });
  });

  describe('Undo Functionality', () => {
    test('canUndo is true after state update', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('new state', 'Test update');
      });

      expect(result.current.canUndo).toBe(true);
    });

    test('undo reverts to previous state', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('second', 'Update 1');
        result.current.updateState('third', 'Update 2');
      });

      act(() => {
        result.current.undo();
      });

      expect(result.current.state).toBe('second');
      expect(result.current.canUndo).toBe(true);
      expect(result.current.canRedo).toBe(true);
    });

    test('undo returns null when no history', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      const undoResult = act(() => result.current.undo());

      expect(undoResult).toBe(null);
      expect(result.current.state).toBe('initial');
    });

    test('canUndo is false after undoing to initial state', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('new state', 'Update');
      });

      act(() => {
        result.current.undo();
      });

      expect(result.current.canUndo).toBe(false);
    });
  });

  describe('Redo Functionality', () => {
    test('canRedo is true after undo', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('second', 'Update');
        result.current.undo();
      });

      expect(result.current.canRedo).toBe(true);
    });

    test('redo restores undone state', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('second', 'Update 1');
        result.current.updateState('third', 'Update 2');
        result.current.undo();
      });

      act(() => {
        result.current.redo();
      });

      expect(result.current.state).toBe('third');
      expect(result.current.canUndo).toBe(true);
      expect(result.current.canRedo).toBe(false);
    });

    test('redo returns null when no redo history', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      const redoResult = act(() => result.current.redo());

      expect(redoResult).toBe(null);
    });

    test('canRedo is false after redoing all changes', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('second', 'Update');
      });

      act(() => {
        result.current.undo();
      });

      act(() => {
        result.current.redo();
      });

      expect(result.current.canRedo).toBe(false);
    });
  });

  describe('History Management', () => {
    test('clearHistory resets to current state', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('second', 'Update 1');
        result.current.updateState('third', 'Update 2');
        result.current.updateState('fourth', 'Update 3');
      });

      expect(result.current.canUndo).toBe(true);

      act(() => {
        result.current.clearHistory();
      });

      expect(result.current.canUndo).toBe(false);
      expect(result.current.canRedo).toBe(false);
      expect(result.current.state).toBe('fourth');
    });

    test('getHistory returns current state', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('second', 'Update');
      });

      const history = result.current.getHistory();

      expect(history.canUndo).toBe(true);
      expect(history.canRedo).toBe(false);
      expect(history.currentIndex).toBe(1);
      expect(history.history).toHaveLength(2);
    });

    test('maxHistory limits history size', () => {
      const { result } = renderHook(() => useUndoRedo('initial', { maxHistory: 3 }));

      act(() => {
        result.current.updateState('2', 'Update 2');
        result.current.updateState('3', 'Update 3');
        result.current.updateState('4', 'Update 4');
        result.current.updateState('5', 'Update 5');
      });

      const history = result.current.getHistory();
      expect(history.history.length).toBeLessThanOrEqual(3);
    });
  });

  describe('Function Update Support', () => {
    test('supports function-based state updates', () => {
      const { result } = renderHook(() => useUndoRedo(0));

      act(() => {
        result.current.updateState((prev: number) => prev + 1, 'Increment');
      });

      expect(result.current.state).toBe(1);
    });

    test('function updates access previous state', () => {
      const { result } = renderHook(() => useUndoRedo({ count: 0 }));

      act(() => {
        result.current.updateState((prev: any) => ({ count: prev.count + 1 }), 'Increment');
      });

      expect(result.current.state).toEqual({ count: 1 });
    });
  });

  describe('Debounce Option', () => {
    test('debounces updates when enabled', async () => {
      jest.useFakeTimers();
      const { result } = renderHook(() => useUndoRedo('initial', { debounceMs: 100, enableDebounce: true }));

      act(() => {
        result.current.updateState('state1', 'Update 1');
        result.current.updateState('state2', 'Update 2');
        result.current.updateState('state3', 'Update 3');
      });

      // State should be updated immediately
      expect(result.current.state).toBe('state3');

      // But canUndo should not be true until debounce completes
      expect(result.current.canUndo).toBe(false);

      act(() => {
        jest.advanceTimersByTime(100);
      });

      // After debounce, canUndo should be true
      expect(result.current.canUndo).toBe(true);

      jest.useRealTimers();
    });

    test('no debounce when disabled', () => {
      const { result } = renderHook(() => useUndoRedo('initial', { debounceMs: 100, enableDebounce: false }));

      act(() => {
        result.current.updateState('state1', 'Update 1');
      });

      expect(result.current.canUndo).toBe(true);
    });
  });

  describe('Complex State Types', () => {
    test('works with objects', () => {
      const { result } = renderHook(() =>
        useUndoRedo({ name: 'test', value: 0 })
      );

      act(() => {
        result.current.updateState({ name: 'test', value: 1 }, 'Update value');
      });

      expect(result.current.state).toEqual({ name: 'test', value: 1 });
    });

    test('works with arrays', () => {
      const { result } = renderHook(() => useUndoRedo([1, 2, 3]));

      act(() => {
        result.current.updateState([1, 2, 3, 4], 'Add item');
      });

      expect(result.current.state).toEqual([1, 2, 3, 4]);
    });

    test('handles nested object updates', () => {
      const { result } = renderHook(() =>
        useUndoRedo({ nested: { value: 0 } })
      );

      act(() => {
        result.current.updateState({ nested: { value: 1 } }, 'Update nested');
      });

      expect(result.current.state).toEqual({ nested: { value: 1 } });
    });
  });

  describe('Edge Cases', () => {
    test('handles rapid undo/redo operations', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('1', 'Update 1');
        result.current.updateState('2', 'Update 2');
        result.current.updateState('3', 'Update 3');
      });

      act(() => {
        result.current.undo();
        result.current.undo();
        result.current.redo();
        result.current.undo();
      });

      expect(result.current.state).toBe('1');
      expect(result.current.canUndo).toBe(true);
      expect(result.current.canRedo).toBe(true);
    });

    test('handles update with same value as previous', () => {
      const { result } = renderHook(() => useUndoRedo('initial'));

      act(() => {
        result.current.updateState('initial', 'Same value');
      });

      expect(result.current.canUndo).toBe(true);
    });
  });
});
