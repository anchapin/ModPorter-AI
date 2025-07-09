/**
 * API service for communicating with ModPorter AI backend
 * Implements PRD API specifications
 */

import {
  ConversionRequest,
  ConversionResponse,
  ConversionStatus,
  UploadResponse,
  InitiateConversionParams,
  FeedbackCreatePayload, // Added
  FeedbackResponse // Added
} from '../types/api';

// Use relative URL for production (proxied by nginx) or localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.MODE === 'production' ? '/api/v1' : 'http://localhost:8080/api/v1');

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

  // Step 2: Construct the ConversionRequest payload for the backend
  const backendRequestPayload: ConversionRequest = {
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

export const downloadResult = async (jobId: string): Promise<Blob> => {
  const response = await fetch(`${API_BASE_URL}/convert/${jobId}/download`);
  
  if (!response.ok) {
    throw new ApiError('Download failed', response.status);
  }

  return response.blob();
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