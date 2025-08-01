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
  FeedbackResponse // Added
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
  // TODO: Replace with actual API call: PUT /addons/{addonId}/assets/{assetId}
  console.log(`API: Mock replacing asset for addonId: ${addonId}, assetId: ${assetId}, file: ${file.name}`);

  return new Promise((resolve) => {
    setTimeout(() => {
      // Find the asset in the mocked AddonDetails (if it were fetched and stored locally for mock)
      // For now, just return a new object as if it were updated.
      const updatedAsset: AddonAsset = {
        id: assetId,
        addon_id: addonId,
        type: 'texture_block', // Assuming type doesn't change or is re-evaluated by backend
        path: `simulated/updated_path/${file.name}`,
        original_filename: file.name,
        created_at: new Date(Date.now() - 100000).toISOString(), // Older created_at
        updated_at: new Date().toISOString(), // New updated_at
      };
      console.log("API: Mock asset updated", updatedAsset);
      resolve(updatedAsset);
    }, 300);
  });
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