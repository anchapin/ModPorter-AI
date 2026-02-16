/**
 * API service for communicating with ModPorter AI backend
 * Implements PRD API specifications
 */

import {
  ConversionResponse,
  ConversionStatus,
  UploadResponse,
  InitiateConversionParams,
  AddonDetails, // Added for Addon Editor
  AddonAsset,    // Added for Asset Management
  AddonDataUpload, // Added for saving addon details
  FeedbackCreatePayload, // Added
  FeedbackResponse, // Added
  ConversionAsset, // Added for Conversion Asset Management
  ConversionAssetBatchResult // Added for Conversion Asset Management
} from '../types/api';

// Use relative URL for production (proxied by nginx) or localhost for development
export const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '/api/v1' 
  : 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

export const uploadFile = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file); // Match backend parameter name 'file'

  const response = await fetch(`${API_BASE_URL}/upload`, { // Corrected endpoint
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Upload failed with unknown error' }));
    throw new ApiError(errorData.detail || 'File upload failed', response.status);
  }

  return response.json();
};

export const convertMod = async (params: InitiateConversionParams): Promise<ConversionResponse> => {
  if (!params.file) {
    // As per instructions, conversion via modUrl alone without a file upload step is not currently supported
    // by the backend's /api/v1/convert endpoint (which is start_conversion).
    throw new Error("File is required for conversion.");
  }

  // Step 1: Upload the file
  const uploadResponse = await uploadFile(params.file);

  // Step 2: Construct the backend request payload
  const backendRequestPayload = {
    file_id: uploadResponse.file_id,
    original_filename: uploadResponse.original_filename,
    target_version: params.target_version, // Pass through target_version
    options: {
      smartAssumptions: params.smartAssumptions,
      includeDependencies: params.includeDependencies,
      // modUrl can be part of options if needed by backend logic tied to a file_id
      ...(params.modUrl && { modUrl: params.modUrl }),
    },
  };

  const response = await fetch(`${API_BASE_URL}/convert`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(backendRequestPayload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorData.detail || 'Conversion failed', response.status);
  }

  return response.json();
};

export const getConversionStatus = async (jobId: string): Promise<ConversionStatus> => {
  const response = await fetch(`${API_BASE_URL}/convert/${jobId}/status`);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorData.detail || 'Failed to get status', response.status);
  }

  return response.json();
};

export const downloadResult = async (jobId: string): Promise<{ blob: Blob; filename: string }> => {
  const response = await fetch(`${API_BASE_URL}/convert/${jobId}/download`);
  
  if (!response.ok) {
    throw new ApiError('Download failed', response.status);
  }

  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers.get('Content-Disposition') || response.headers.get('content-disposition');
  let filename = `converted-mod-${jobId}.mcaddon`; // fallback to UUID-based name
  
  if (contentDisposition) {
    const fileNameMatch = contentDisposition.match(/filename="([^"]+)"/);
    if (fileNameMatch) {
      filename = fileNameMatch[1];
    }
  }

  const blob = await response.blob();
  return { blob, filename };
};

export const cancelJob = async (jobId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/convert/${jobId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorData.detail || 'Failed to cancel job', response.status);
  }
};

// --- Addon Editor API Functions ---

export const getAddonDetails = async (addonId: string): Promise<AddonDetails> => {
  console.log(`API: Fetching details for addonId: ${addonId}`);
  const response = await fetch(`${API_BASE_URL}/addons/${addonId}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `Failed to fetch addon details for ${addonId}` }));
    throw new ApiError(errorData.detail || `Failed to get addon details (status: ${response.status})`, response.status);
  }
  return response.json();
};

export const saveAddonDetails = async (addonId: string, data: AddonDataUpload): Promise<AddonDetails> => {
  console.log(`API: Saving details for addonId: ${addonId}`, data);
  const response = await fetch(`${API_BASE_URL}/addons/${addonId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `Failed to save addon details for ${addonId}` }));
    throw new ApiError(errorData.detail || `Failed to save addon details (status: ${response.status})`, response.status);
  }
  return response.json(); // Backend returns the full updated AddonDetails
};

export const uploadAddonAsset = async (addonId: string, file: File, assetType: string): Promise<AddonAsset> => {
  console.log(`API: Uploading asset for addonId: ${addonId}, file: ${file.name}, type: ${assetType}`);
  const formData = new FormData();
  formData.append('file', file);
  formData.append('asset_type', assetType); // Backend expects asset_type as form data

  const response = await fetch(`${API_BASE_URL}/addons/${addonId}/assets`, {
    method: 'POST',
    body: formData,
    // Headers are not typically 'Content-Type: application/json' for FormData,
    // the browser sets it to 'multipart/form-data' automatically with boundary.
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to upload asset' }));
    throw new ApiError(errorData.detail || `Asset upload failed (status: ${response.status})`, response.status);
  }
  return response.json();
};

export const replaceAddonAsset = async (addonId: string, assetId: string, file: File): Promise<AddonAsset> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/addons/${addonId}/assets/${assetId}`, {
    method: 'PUT',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to replace asset' }));
    throw new ApiError(errorData.detail || `Asset replacement failed (status: ${response.status})`, response.status);
  }
  return response.json();
};

export const deleteAddonAssetAPI = async (addonId: string, assetId: string): Promise<void> => {
  console.log(`API: Deleting asset for addonId: ${addonId}, assetId: ${assetId}`);
  const response = await fetch(`${API_BASE_URL}/addons/${addonId}/assets/${assetId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    // For 204 No Content, response.json() will fail if called.
    // However, !response.ok means status is not 200-299.
    // So if status is not 204, it's an error with a body.
    if (response.status === 204) {
      // This case should not be hit if !response.ok, but good for clarity.
      // If backend returns 204, response.ok would be true.
      return;
    }
    const errorData = await response.json().catch(() => ({ detail: 'Failed to delete asset' }));
    throw new ApiError(errorData.detail || `Asset deletion failed (status: ${response.status})`, response.status);
  }
  // If response.ok is true, and it's a DELETE, it's typically 204 No Content or 200 OK with a body.
  // If 204, no body to parse. If 200, there might be.
  // The promise is Promise<void>, so no return value is expected on success.
};

// Performance Benchmarking API
export const performanceBenchmarkAPI = {
  // Get all available scenarios
  getScenarios: async () => {
    const response = await fetch(`${API_BASE_URL}/performance/scenarios`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(errorData.detail || 'Failed to fetch scenarios', response.status);
    }
    
    return { data: await response.json() };
  },

  // Run a benchmark
  runBenchmark: async (request: {
    scenario_id: string;
    device_type?: string;
    conversion_id?: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/performance/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        scenario_id: request.scenario_id,
        device_type: request.device_type || 'desktop',
        conversion_id: request.conversion_id,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(errorData.detail || 'Failed to start benchmark', response.status);
    }

    return { data: await response.json() };
  },

  // Get benchmark status
  getBenchmarkStatus: async (runId: string) => {
    const response = await fetch(`${API_BASE_URL}/performance/status/${runId}`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(errorData.detail || 'Failed to get benchmark status', response.status);
    }
    
    return { data: await response.json() };
  },

  // Get benchmark report
  getBenchmarkReport: async (runId: string) => {
    const response = await fetch(`${API_BASE_URL}/performance/report/${runId}`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(errorData.detail || 'Failed to get benchmark report', response.status);
    }
    
    return { data: await response.json() };
  },

  // Create custom scenario
  createCustomScenario: async (scenario: {
    scenario_name: string;
    description: string;
    type: string;
    duration_seconds?: number;
    parameters?: Record<string, any>;
    thresholds?: Record<string, number>;
  }) => {
    const response = await fetch(`${API_BASE_URL}/performance/scenarios`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        scenario_name: scenario.scenario_name,
        description: scenario.description,
        type: scenario.type,
        duration_seconds: scenario.duration_seconds || 300,
        parameters: scenario.parameters || {},
        thresholds: scenario.thresholds || {},
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(errorData.detail || 'Failed to create custom scenario', response.status);
    }

    return { data: await response.json() };
  },

  // Get benchmark history
  getBenchmarkHistory: async (limit: number = 50, offset: number = 0) => {
    const response = await fetch(`${API_BASE_URL}/performance/history?limit=${limit}&offset=${offset}`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(errorData.detail || 'Failed to get benchmark history', response.status);
    }
    
    return { data: await response.json() };
  },
};

export const submitFeedback = async (payload: FeedbackCreatePayload): Promise<FeedbackResponse> => {
  const response = await fetch(`${API_BASE_URL}/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error submitting feedback' }));
    throw new ApiError(errorData.detail || 'Failed to submit feedback', response.status);
  }

  return response.json();
};

// --- Conversion Asset Management API Functions ---

export const listConversionAssets = async (
  conversionId: string,
  assetType?: string,
  status?: string,
  skip: number = 0,
  limit: number = 100
): Promise<ConversionAsset[]> => {
  const params = new URLSearchParams({
    skip: skip.toString(),
    limit: limit.toString(),
  });
  
  if (assetType) params.append('asset_type', assetType);
  if (status) params.append('status', status);

  const response = await fetch(
    `${API_BASE_URL}/conversions/${conversionId}/assets?${params.toString()}`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to list assets' }));
    throw new ApiError(errorData.detail || 'Failed to list conversion assets', response.status);
  }

  return response.json();
};

export const uploadConversionAsset = async (
  conversionId: string,
  file: File,
  assetType: string
): Promise<ConversionAsset> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('asset_type', assetType);

  const response = await fetch(`${API_BASE_URL}/conversions/${conversionId}/assets`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new ApiError(errorData.detail || 'Failed to upload asset', response.status);
  }

  return response.json();
};

export const getConversionAsset = async (assetId: string): Promise<ConversionAsset> => {
  const response = await fetch(`${API_BASE_URL}/assets/${assetId}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Asset not found' }));
    throw new ApiError(errorData.detail || 'Failed to get asset', response.status);
  }

  return response.json();
};

export const updateConversionAssetStatus = async (
  assetId: string,
  status: string,
  convertedPath?: string,
  errorMessage?: string
): Promise<ConversionAsset> => {
  const response = await fetch(`${API_BASE_URL}/assets/${assetId}/status`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      status,
      converted_path: convertedPath,
      error_message: errorMessage,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Update failed' }));
    throw new ApiError(errorData.detail || 'Failed to update asset status', response.status);
  }

  return response.json();
};

export const updateConversionAssetMetadata = async (
  assetId: string,
  metadata: Record<string, any>
): Promise<ConversionAsset> => {
  const response = await fetch(`${API_BASE_URL}/assets/${assetId}/metadata`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(metadata),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Update failed' }));
    throw new ApiError(errorData.detail || 'Failed to update asset metadata', response.status);
  }

  return response.json();
};

export const deleteConversionAsset = async (assetId: string): Promise<{ message: string }> => {
  const response = await fetch(`${API_BASE_URL}/assets/${assetId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Delete failed' }));
    throw new ApiError(errorData.detail || 'Failed to delete asset', response.status);
  }

  return response.json();
};

export const convertConversionAsset = async (assetId: string): Promise<ConversionAsset> => {
  const response = await fetch(`${API_BASE_URL}/assets/${assetId}/convert`, {
    method: 'POST',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Conversion failed' }));
    throw new ApiError(errorData.detail || 'Failed to convert asset', response.status);
  }

  return response.json();
};

export const convertAllConversionAssets = async (conversionId: string): Promise<ConversionAssetBatchResult> => {
  const response = await fetch(`${API_BASE_URL}/conversions/${conversionId}/assets/convert-all`, {
    method: 'POST',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Batch conversion failed' }));
    throw new ApiError(errorData.detail || 'Failed to convert assets', response.status);
  }

  return response.json();
};

// --- Behavior Templates API Functions ---

export interface BehaviorTemplateCategory {
  name: string;
  display_name: string;
  description: string;
  icon?: string;
}

export interface BehaviorTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  template_type: string;
  template_data: Record<string, any>;
  tags: string[];
  is_public: boolean;
  version: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface BehaviorTemplateCreate {
  name: string;
  description: string;
  category: string;
  template_type: string;
  template_data: Record<string, any>;
  tags?: string[];
  is_public?: boolean;
  version?: string;
}

export interface BehaviorTemplateUpdate {
  name?: string;
  description?: string;
  category?: string;
  template_type?: string;
  template_data?: Record<string, any>;
  tags?: string[];
  is_public?: boolean;
  version?: string;
}

export interface TemplateApplyRequest {
  template_id: string;
  conversion_id: string;
  file_path?: string;
}

export interface TemplateApplyResult {
  template_id: string;
  conversion_id: string;
  generated_content?: any;
  file_path?: string;
  file_type?: string;
  applied_at: string;
}

export interface BehaviorPackExportRequest {
  conversion_id: string;
  file_types?: string[];
  include_templates?: boolean;
  export_format?: 'mcaddon' | 'zip' | 'json';
}

export interface BehaviorPackExportResponse {
  conversion_id: string;
  export_format: string;
  file_count: number;
  template_count: number;
  export_size: number;
  exported_at: string;
}

export const behaviorTemplatesAPI = {
  // Get template categories
  getCategories: async (): Promise<BehaviorTemplateCategory[]> => {
    const response = await fetch(`${API_BASE_URL}/behavior/templates/categories`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch categories' }));
      throw new ApiError(errorData.detail || 'Failed to get template categories', response.status);
    }
    
    return response.json();
  },

  // Get templates with filtering
  getTemplates: async (params?: {
    category?: string;
    template_type?: string;
    tags?: string[];
    search?: string;
    is_public?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<BehaviorTemplate[]> => {
    const searchParams = new URLSearchParams();
    
    if (params?.category) searchParams.append('category', params.category);
    if (params?.template_type) searchParams.append('template_type', params.template_type);
    if (params?.tags?.length) searchParams.append('tags', params.tags.join(','));
    if (params?.search) searchParams.append('search', params.search);
    if (params?.is_public !== undefined) searchParams.append('is_public', params.is_public.toString());
    if (params?.skip !== undefined) searchParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) searchParams.append('limit', params.limit.toString());

    const response = await fetch(
      `${API_BASE_URL}/behavior/templates?${searchParams.toString()}`
    );
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch templates' }));
      throw new ApiError(errorData.detail || 'Failed to get templates', response.status);
    }
    
    return response.json();
  },

  // Get specific template
  getTemplate: async (templateId: string): Promise<BehaviorTemplate> => {
    const response = await fetch(`${API_BASE_URL}/behavior/templates/${templateId}`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Template not found' }));
      throw new ApiError(errorData.detail || 'Failed to get template', response.status);
    }
    
    return response.json();
  },

  // Create template
  createTemplate: async (template: BehaviorTemplateCreate): Promise<BehaviorTemplate> => {
    const response = await fetch(`${API_BASE_URL}/behavior/templates`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(template),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to create template' }));
      throw new ApiError(errorData.detail || 'Failed to create template', response.status);
    }
    
    return response.json();
  },

  // Update template
  updateTemplate: async (templateId: string, updates: BehaviorTemplateUpdate): Promise<BehaviorTemplate> => {
    const response = await fetch(`${API_BASE_URL}/behavior/templates/${templateId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to update template' }));
      throw new ApiError(errorData.detail || 'Failed to update template', response.status);
    }
    
    return response.json();
  },

  // Delete template
  deleteTemplate: async (templateId: string): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/behavior/templates/${templateId}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to delete template' }));
      throw new ApiError(errorData.detail || 'Failed to delete template', response.status);
    }
  },

  // Apply template to conversion
  applyTemplate: async (request: TemplateApplyRequest): Promise<TemplateApplyResult> => {
    const searchParams = new URLSearchParams();
    if (request.file_path) searchParams.append('file_path', request.file_path);
    if (request.conversion_id) searchParams.append('conversion_id', request.conversion_id);

    const response = await fetch(
      `${API_BASE_URL}/behavior/templates/${request.template_id}/apply?${searchParams.toString()}`,
      {
        method: 'GET',
      }
    );
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to apply template' }));
      throw new ApiError(errorData.detail || 'Failed to apply template', response.status);
    }
    
    return response.json();
  },

  // Get predefined templates
  getPredefinedTemplates: async (): Promise<BehaviorTemplate[]> => {
    const response = await fetch(`${API_BASE_URL}/behavior/templates/predefined`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch predefined templates' }));
      throw new ApiError(errorData.detail || 'Failed to get predefined templates', response.status);
    }
    
    return response.json();
  },
};

// --- Behavior Export API Functions ---

export const behaviorExportAPI = {
  // Export behavior pack
  exportBehaviorPack: async (request: BehaviorPackExportRequest): Promise<BehaviorPackExportResponse> => {
    const response = await fetch(`${API_BASE_URL}/behavior/export/behavior-pack`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to export behavior pack' }));
      throw new ApiError(errorData.detail || 'Failed to export behavior pack', response.status);
    }
    
    return response.json();
  },

  // Download exported pack
  downloadPack: async (conversionId: string, format: string = 'mcaddon'): Promise<{ blob: Blob; filename: string }> => {
    const response = await fetch(`${API_BASE_URL}/behavior/export/behavior-pack/${conversionId}/download?format=${format}`);
    
    if (!response.ok) {
      throw new ApiError('Download failed', response.status);
    }

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition') || response.headers.get('content-disposition');
    let filename = `behavior_pack_${conversionId}.${format}`;
    
    if (contentDisposition) {
      const fileNameMatch = contentDisposition.match(/filename="([^"]+)"/);
      if (fileNameMatch) {
        filename = fileNameMatch[1];
      }
    }

    const blob = await response.blob();
    return { blob, filename };
  },

  // Get export formats
  getExportFormats: async (): Promise<Array<{ format: string; name: string; description: string; extension: string }>> => {
    const response = await fetch(`${API_BASE_URL}/behavior/export/formats`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch export formats' }));
      throw new ApiError(errorData.detail || 'Failed to get export formats', response.status);
    }
    
    return response.json();
  },

  // Preview export
  previewExport: async (conversionId: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/behavior/export/preview/${conversionId}`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to preview export' }));
      throw new ApiError(errorData.detail || 'Failed to preview export', response.status);
    }
    
    return response.json();
  },
};