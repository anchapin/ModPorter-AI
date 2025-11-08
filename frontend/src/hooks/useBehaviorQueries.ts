import { useQuery, useMutation, useQueryClient, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import {
  behaviorTemplatesAPI,
  behaviorExportAPI,
  BehaviorTemplate,
  BehaviorTemplateCategory,
  BehaviorTemplateCreate,
  BehaviorTemplateUpdate,
  TemplateApplyRequest,
  BehaviorPackExportRequest,
  BehaviorPackExportResponse,
} from '../services/api';

// Query keys
export const BEHAVIOR_TEMPLATES_QUERY_KEYS = {
  all: ['behavior-templates'] as const,
  categories: ['behavior-templates', 'categories'] as const,
  templates: (filters: any) => ['behavior-templates', 'templates', filters] as const,
  template: (id: string) => ['behavior-templates', 'template', id] as const,
  predefined: ['behavior-templates', 'predefined'] as const,
  exportPreview: (conversionId: string) => ['behavior-export', 'preview', conversionId] as const,
  exportFormats: ['behavior-export', 'formats'] as const,
} as const;

// Hook for getting template categories
export const useBehaviorTemplateCategories = (options?: UseQueryOptions<BehaviorTemplateCategory[]>) => {
  return useQuery({
    queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.categories,
    queryFn: () => behaviorTemplatesAPI.getCategories(),
    ...options,
  });
};

// Hook for getting templates with filters
export const useBehaviorTemplates = (
  filters?: {
    category?: string;
    template_type?: string;
    tags?: string[];
    search?: string;
    is_public?: boolean;
    skip?: number;
    limit?: number;
  },
  options?: UseQueryOptions<BehaviorTemplate[]>
) => {
  return useQuery({
    queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.templates(filters || {}),
    queryFn: () => behaviorTemplatesAPI.getTemplates(filters),
    ...options,
  });
};

// Hook for getting predefined templates
export const usePredefinedBehaviorTemplates = (options?: UseQueryOptions<BehaviorTemplate[]>) => {
  return useQuery({
    queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.predefined,
    queryFn: () => behaviorTemplatesAPI.getPredefinedTemplates(),
    ...options,
  });
};

// Hook for getting specific template
export const useBehaviorTemplate = (
  templateId: string,
  options?: UseQueryOptions<BehaviorTemplate>
) => {
  return useQuery({
    queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.template(templateId),
    queryFn: () => behaviorTemplatesAPI.getTemplate(templateId),
    enabled: !!templateId,
    ...options,
  });
};

// Hook for creating template
export const useCreateBehaviorTemplate = (
  options?: UseMutationOptions<BehaviorTemplate, Error, BehaviorTemplateCreate>
) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (template: BehaviorTemplateCreate) => 
      behaviorTemplatesAPI.createTemplate(template),
    onSuccess: (newTemplate) => {
      // Invalidate templates list
      queryClient.invalidateQueries({ queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.templates({}) });
      
      // Add to specific queries if they exist
      queryClient.setQueriesData(
        { 
          queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.templates({}) 
        },
        (old: BehaviorTemplate[] | undefined) => 
          old ? [newTemplate, ...old] : [newTemplate]
      );
    },
    ...options,
  });
};

// Hook for updating template
export const useUpdateBehaviorTemplate = (
  options?: UseMutationOptions<BehaviorTemplate, Error, { templateId: string; updates: BehaviorTemplateUpdate }>
) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ templateId, updates }) => 
      behaviorTemplatesAPI.updateTemplate(templateId, updates),
    onSuccess: (updatedTemplate) => {
      // Update cache for the specific template
      queryClient.setQueryData(
        BEHAVIOR_TEMPLATES_QUERY_KEYS.template(updatedTemplate.id),
        updatedTemplate
      );
      
      // Update in all template lists
      queryClient.setQueriesData(
        { 
          queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.templates({}) 
        },
        (old: BehaviorTemplate[] | undefined) => 
          old ? old.map(t => t.id === updatedTemplate.id ? updatedTemplate : t) : [updatedTemplate]
      );
    },
    ...options,
  });
};

// Hook for deleting template
export const useDeleteBehaviorTemplate = (
  options?: UseMutationOptions<void, Error, string>
) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (templateId: string) => 
      behaviorTemplatesAPI.deleteTemplate(templateId),
    onSuccess: (_, templateId) => {
      // Remove from cache
      queryClient.removeQueries({ 
        queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.template(templateId) 
      });
      
      // Update all template lists
      queryClient.setQueriesData(
        { 
          queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.templates({}) 
        },
        (old: BehaviorTemplate[] | undefined) => 
          old ? old.filter(t => t.id !== templateId) : []
      );
    },
    ...options,
  });
};

// Hook for applying template
export const useApplyBehaviorTemplate = (
  options?: UseMutationOptions<any, Error, TemplateApplyRequest>
) => {
  return useMutation({
    mutationFn: (request: TemplateApplyRequest) => 
      behaviorTemplatesAPI.applyTemplate(request),
    ...options,
  });
};

// Hook for export preview
export const useBehaviorExportPreview = (
  conversionId: string,
  options?: UseQueryOptions<any>
) => {
  return useQuery({
    queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.exportPreview(conversionId),
    queryFn: () => behaviorExportAPI.previewExport(conversionId),
    enabled: !!conversionId,
    ...options,
  });
};

// Hook for export formats
export const useBehaviorExportFormats = (options?: UseQueryOptions<Array<{ format: string; name: string; description: string; extension: string }>>) => {
  return useQuery({
    queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.exportFormats,
    queryFn: () => behaviorExportAPI.getExportFormats(),
    ...options,
  });
};

// Hook for exporting behavior pack
export const useExportBehaviorPack = (
  options?: UseMutationOptions<BehaviorPackExportResponse, Error, BehaviorPackExportRequest>
) => {
  return useMutation({
    mutationFn: (request: BehaviorPackExportRequest) => 
      behaviorExportAPI.exportBehaviorPack(request),
    ...options,
  });
};

// Hook for downloading exported pack
export const useDownloadBehaviorPack = (
  options?: UseMutationOptions<{ blob: Blob; filename: string }, Error, { conversionId: string; format?: string }>
) => {
  return useMutation({
    mutationFn: ({ conversionId, format }) => 
      behaviorExportAPI.downloadPack(conversionId, format),
    onSuccess: ({ blob, filename }) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
    ...options,
  });
};

// Utility hook for invalidating all template-related queries
export const useInvalidateBehaviorTemplates = () => {
  const queryClient = useQueryClient();
  
  return () => {
    queryClient.invalidateQueries({ queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.all });
  };
};

// Utility hook for prefetching templates
export const usePrefetchBehaviorTemplates = () => {
  const queryClient = useQueryClient();
  
  return (filters?: any) => {
    queryClient.prefetchQuery({
      queryKey: BEHAVIOR_TEMPLATES_QUERY_KEYS.templates(filters || {}),
      queryFn: () => behaviorTemplatesAPI.getTemplates(filters),
    });
  };
};

// Utility hook for getting combined templates (predefined + custom)
export const useCombinedBehaviorTemplates = (
  filters?: any,
  options?: UseQueryOptions<BehaviorTemplate[]>
) => {
  const predefined = usePredefinedBehaviorTemplates();
  const custom = useBehaviorTemplates(filters);
  
  return {
    ...predefined,
    ...custom,
    data: [
      ...(predefined.data || []),
      ...(custom.data || [])
    ],
    isLoading: predefined.isLoading || custom.isLoading,
    isError: predefined.isError || custom.isError,
    error: predefined.error || custom.error,
  };
};
