import React, { useState, useCallback } from 'react';
import { useToast, ToastMessage } from '../components/common/Toast';

interface LoadingState {
  [key: string]: boolean;
}

interface ErrorState {
  [key: string]: string | null;
}

export interface UseUIStateReturn {
  loading: LoadingState;
  error: ErrorState;
  setLoading: (key: string, value: boolean) => void;
  setIsLoading: (key: string, value: boolean) => void;
  setError: (key: string, message: string | null) => void;
  clearError: (key?: string) => void;
  clearAllErrors: () => void;
  isLoading: (key: string) => boolean;
  hasError: (key: string) => boolean;
  // Toast methods
  toasts: ToastMessage[];
  toast: ReturnType<typeof useToast>;
}

export const useUIState = (): UseUIStateReturn => {
  const [loading, setLoadingState] = useState<LoadingState>({});
  const [error, setErrorState] = useState<ErrorState>({});
  const toast = useToast();

  const setLoading = useCallback((key: string, value: boolean) => {
    setLoadingState(prev => ({ ...prev, [key]: value }));
  }, []);

  const setIsLoading = setLoading; // Alias for consistency

  const setError = useCallback((key: string, message: string | null) => {
    setErrorState(prev => ({ ...prev, [key]: message }));
  }, []);

  const clearError = useCallback((key?: string) => {
    if (key) {
      setErrorState(prev => ({ ...prev, [key]: null }));
    } else {
      setErrorState({});
    }
  }, []);

  const clearAllErrors = useCallback(() => {
    setErrorState({});
  }, []);

  const isLoading = useCallback((key: string) => {
    return loading[key] || false;
  }, [loading]);

  const hasError = useCallback((key: string) => {
    return !!error[key];
  }, [error]);

  return {
    loading,
    error,
    setLoading,
    setIsLoading,
    setError,
    clearError,
    clearAllErrors,
    isLoading,
    hasError,
    toasts: toast.toasts,
    toast,
  };
};

// Hook for managing form state with validation
export interface UseFormStateReturn<T> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isValid: boolean;
  isDirty: boolean;
  setFieldValue: (field: keyof T, value: T[keyof T]) => void;
  setFieldError: (field: keyof T, error: string) => void;
  clearFieldError: (field: keyof T) => void;
  clearAllErrors: () => void;
  setTouched: (field: keyof T, touched: boolean) => void;
  setValues: (values: T) => void;
  resetForm: (initialValues?: T) => void;
  validateForm: () => boolean;
}

export const useFormState = <T extends Record<string, any>>(
  initialValues: T,
  validation?: (values: T) => Partial<Record<keyof T, string>>
): UseFormStateReturn<T> => {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});

  const setFieldValue = useCallback((field: keyof T, value: T[keyof T]) => {
    setValues(prev => ({ ...prev, [field]: value }));
    setTouched(prev => ({ ...prev, [field]: true }));
  }, []);

  const setFieldError = useCallback((field: keyof T, error: string) => {
    setErrors(prev => ({ ...prev, [field]: error }));
  }, []);

  const clearFieldError = useCallback((field: keyof T) => {
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[field];
      return newErrors;
    });
  }, []);

  const clearAllErrors = useCallback(() => {
    setErrors({});
  }, []);

  const setFieldTouched = useCallback((field: keyof T, touched: boolean) => {
    setTouched(prev => ({ ...prev, [field]: touched }));
  }, []);

  const validateForm = useCallback(() => {
    if (validation) {
      const newErrors = validation(values);
      setErrors(newErrors);
      return Object.keys(newErrors).length === 0;
    }
    return true;
  }, [values, validation]);

  const isValid = Object.keys(errors).length === 0;
  const isDirty = JSON.stringify(values) !== JSON.stringify(initialValues);

  const resetForm = useCallback((newInitialValues?: T) => {
    const resetValues = newInitialValues || initialValues;
    setValues(resetValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  return {
    values,
    errors,
    touched,
    isValid,
    isDirty,
    setFieldValue,
    setFieldError,
    clearFieldError,
    clearAllErrors,
    setTouched: setFieldTouched,
    setValues,
    resetForm,
    validateForm,
  };
};

// Hook for managing async operations with loading and error states
export interface UseAsyncOperationReturn {
  loading: boolean;
  error: string | null;
  execute: () => Promise<any>;
  reset: () => void;
}

export const useAsyncOperation = (
  operation: () => Promise<any>,
  options: {
    onSuccess?: (result: any) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
    showToast?: boolean;
    successMessage?: string;
  } = {}
): UseAsyncOperationReturn => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const execute = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await operation();
      
      if (options.onSuccess) {
        options.onSuccess(result);
      }
      
      if (options.showToast && options.successMessage) {
        toast.success(options.successMessage);
      }
      
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);
      
      if (options.onError) {
        options.onError(err instanceof Error ? err : new Error(errorMessage));
      }
      
      if (options.showToast) {
        toast.error(errorMessage);
      }
      
      throw err;
    } finally {
      setLoading(false);
      if (options.onComplete) {
        options.onComplete();
      }
    }
  }, [operation, options, toast]);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
  }, []);

  return {
    loading,
    error,
    execute,
    reset,
  };
};

// Hook for managing debounced operations
export interface UseDebounceReturn {
  debouncedValue: any;
  cancel: () => void;
  flush: () => void;
}

export const useDebounce = (
  value: any,
  delay: number
): UseDebounceReturn => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  const cancel = useCallback(() => {
    // Implementation will use timeout ref
  }, []);

  const flush = useCallback(() => {
    setDebouncedValue(value);
  }, [value]);

  // In a real implementation, you'd use setTimeout here
  // For now, just sync the values
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return {
    debouncedValue,
    cancel,
    flush,
  };
};

export default useUIState;
