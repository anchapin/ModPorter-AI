import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { 
  behaviorTemplatesAPI, 
  BehaviorTemplate, 
  BehaviorTemplateCategory,
  BehaviorTemplateCreate,
  BehaviorTemplateUpdate
} from '../services/api';

// State interface
interface TemplatesState {
  categories: BehaviorTemplateCategory[];
  templates: BehaviorTemplate[];
  currentTemplate: BehaviorTemplate | null;
  loading: boolean;
  error: string | null;
  filters: {
    category?: string;
    template_type?: string;
    search?: string;
    is_public?: boolean;
  };
  pagination: {
    skip: number;
    limit: number;
    hasMore: boolean;
  };
}

// Action types
type TemplatesAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_CATEGORIES'; payload: BehaviorTemplateCategory[] }
  | { type: 'SET_TEMPLATES'; payload: BehaviorTemplate[] }
  | { type: 'ADD_TEMPLATES'; payload: BehaviorTemplate[] }
  | { type: 'SET_CURRENT_TEMPLATE'; payload: BehaviorTemplate | null }
  | { type: 'SET_FILTERS'; payload: Partial<TemplatesState['filters']> }
  | { type: 'SET_PAGINATION'; payload: Partial<TemplatesState['pagination']> }
  | { type: 'UPDATE_TEMPLATE'; payload: BehaviorTemplate }
  | { type: 'REMOVE_TEMPLATE'; payload: string }
  | { type: 'RESET' };

// Initial state
const initialState: TemplatesState = {
  categories: [],
  templates: [],
  currentTemplate: null,
  loading: false,
  error: null,
  filters: {},
  pagination: {
    skip: 0,
    limit: 50,
    hasMore: true,
  },
};

// Reducer
const templatesReducer = (state: TemplatesState, action: TemplatesAction): TemplatesState => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    
    case 'SET_CATEGORIES':
      return { ...state, categories: action.payload };
    
    case 'SET_TEMPLATES':
      return { ...state, templates: action.payload, pagination: { ...state.pagination, hasMore: action.payload.length >= state.pagination.limit } };
    
    case 'ADD_TEMPLATES':
      return { 
        ...state, 
        templates: [...state.templates, ...action.payload],
        pagination: { ...state.pagination, hasMore: action.payload.length >= state.pagination.limit }
      };
    
    case 'SET_CURRENT_TEMPLATE':
      return { ...state, currentTemplate: action.payload };
    
    case 'SET_FILTERS':
      return { 
        ...state, 
        filters: { ...state.filters, ...action.payload },
        pagination: { ...initialState.pagination } // Reset pagination when filters change
      };
    
    case 'SET_PAGINATION':
      return { ...state, pagination: { ...state.pagination, ...action.payload } };
    
    case 'UPDATE_TEMPLATE':
      return {
        ...state,
        templates: state.templates.map(template =>
          template.id === action.payload.id ? action.payload : template
        ),
        currentTemplate: state.currentTemplate?.id === action.payload.id ? action.payload : state.currentTemplate,
      };
    
    case 'REMOVE_TEMPLATE':
      return {
        ...state,
        templates: state.templates.filter(template => template.id !== action.payload),
        currentTemplate: state.currentTemplate?.id === action.payload ? null : state.currentTemplate,
      };
    
    case 'RESET':
      return initialState;
    
    default:
      return state;
  }
};

// Context
const TemplatesContext = createContext<{
  state: TemplatesState;
  actions: {
    loadCategories: () => Promise<void>;
    loadTemplates: (reset?: boolean) => Promise<void>;
    loadTemplate: (templateId: string) => Promise<void>;
    createTemplate: (template: BehaviorTemplateCreate) => Promise<BehaviorTemplate>;
    updateTemplate: (templateId: string, updates: BehaviorTemplateUpdate) => Promise<BehaviorTemplate>;
    deleteTemplate: (templateId: string) => Promise<void>;
    setFilters: (filters: Partial<TemplatesState['filters']>) => void;
    loadMore: () => Promise<void>;
    reset: () => void;
    applyTemplate: (templateId: string, conversionId: string, filePath?: string) => Promise<any>;
  };
} | null>(null);

// Provider component
export const TemplatesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(templatesReducer, initialState);

  // Load categories
  const loadCategories = useCallback(async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const categories = await behaviorTemplatesAPI.getCategories();
      dispatch({ type: 'SET_CATEGORIES', payload: categories });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load categories';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  // Load templates with current filters
  const loadTemplates = useCallback(async (reset = false) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_ERROR', payload: null });
      
      const skip = reset ? 0 : state.pagination.skip;
      const templates = await behaviorTemplatesAPI.getTemplates({
        ...state.filters,
        skip,
        limit: state.pagination.limit,
      });

      if (reset) {
        dispatch({ type: 'SET_TEMPLATES', payload: templates });
      } else {
        dispatch({ type: 'ADD_TEMPLATES', payload: templates });
      }
      
      dispatch({ type: 'SET_PAGINATION', payload: { skip: skip + state.pagination.limit } });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load templates';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [state.filters, state.pagination.skip, state.pagination.limit]);

  // Load specific template
  const loadTemplate = useCallback(async (templateId: string) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const template = await behaviorTemplatesAPI.getTemplate(templateId);
      dispatch({ type: 'SET_CURRENT_TEMPLATE', payload: template });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load template';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  // Create template
  const createTemplate = useCallback(async (template: BehaviorTemplateCreate): Promise<BehaviorTemplate> => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const newTemplate = await behaviorTemplatesAPI.createTemplate(template);
      dispatch({ type: 'UPDATE_TEMPLATE', payload: newTemplate });
      return newTemplate;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create template';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
      throw error;
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  // Update template
  const updateTemplate = useCallback(async (templateId: string, updates: BehaviorTemplateUpdate): Promise<BehaviorTemplate> => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const updatedTemplate = await behaviorTemplatesAPI.updateTemplate(templateId, updates);
      dispatch({ type: 'UPDATE_TEMPLATE', payload: updatedTemplate });
      return updatedTemplate;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update template';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
      throw error;
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  // Delete template
  const deleteTemplate = useCallback(async (templateId: string): Promise<void> => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      await behaviorTemplatesAPI.deleteTemplate(templateId);
      dispatch({ type: 'REMOVE_TEMPLATE', payload: templateId });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete template';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
      throw error;
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  // Set filters
  const setFilters = useCallback((filters: Partial<TemplatesState['filters']>) => {
    dispatch({ type: 'SET_FILTERS', payload: filters });
  }, []);

  // Load more templates
  const loadMore = useCallback(async () => {
    if (!state.loading && state.pagination.hasMore) {
      await loadTemplates(false);
    }
  }, [state.loading, state.pagination.hasMore, loadTemplates]);

  // Reset state
  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  // Apply template to conversion
  const applyTemplate = useCallback(async (templateId: string, conversionId: string, filePath?: string) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const result = await behaviorTemplatesAPI.applyTemplate({
        template_id: templateId,
        conversion_id: conversionId,
        file_path: filePath,
      });
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to apply template';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
      throw error;
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  // Load categories on mount
  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  // Load templates when filters change
  useEffect(() => {
    loadTemplates(true);
  }, [state.filters, loadTemplates]); // eslint-disable-line react-hooks/exhaustive-deps

  const actions = {
    loadCategories,
    loadTemplates,
    loadTemplate,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    setFilters,
    loadMore,
    reset,
    applyTemplate,
  };

  return (
    <TemplatesContext.Provider value={{ state, actions }}>
      {children}
    </TemplatesContext.Provider>
  );
};

// Hook to use the context
export const useTemplates = () => {
  const context = useContext(TemplatesContext);
  if (!context) {
    throw new Error('useTemplates must be used within a TemplatesProvider');
  }
  return context;
};
